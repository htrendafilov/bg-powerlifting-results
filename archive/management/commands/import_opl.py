"""Import an OpenPowerlifting export.

The federation's own protocols only cover meets held in Bulgaria. Bulgarians
lifting abroad appear in the OpenPowerlifting bulk export, whose CSV data is
contributed to the public domain, so it is the source used here rather than
scraping a results site.
"""

import csv
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from archive.models import (
    AgeGroup,
    Competition,
    Equipment,
    Event,
    MeetLevel,
    Result,
    Sex,
    unique_slug,
)
from archive.services.commit import athlete_for
from archive.services.names import transliterate
from archive.services.records import recalculate_records

EVENTS = {"SBD": Event.SBD, "B": Event.B, "D": Event.D, "BD": Event.PP}
EQUIPMENT = {
    "Raw": Equipment.CLASSIC,
    "Wraps": Equipment.CLASSIC,
    "Single-ply": Equipment.EQUIPPED,
    "Multi-ply": Equipment.EQUIPPED,
    "Unlimited": Equipment.EQUIPPED,
}
DIVISIONS = {
    "open": AgeGroup.OPEN,
    "o": AgeGroup.OPEN,
    "juniors": AgeGroup.JUNIOR,
    "junior": AgeGroup.JUNIOR,
    "sub-juniors": AgeGroup.SUBJUNIOR,
    "sub-junior": AgeGroup.SUBJUNIOR,
    "masters 1": AgeGroup.M1,
    "masters 2": AgeGroup.M2,
    "masters 3": AgeGroup.M3,
    "masters 4": AgeGroup.M4,
}
# Used when the division is something the meet invented ("Prime Time", "Guest").
BIRTH_YEAR_CLASS = [
    ("14-18", AgeGroup.SUBJUNIOR),
    ("19-23", AgeGroup.JUNIOR),
    ("24-39", AgeGroup.OPEN),
    ("40-49", AgeGroup.M1),
    ("50-59", AgeGroup.M2),
    ("60-69", AgeGroup.M3),
]
ATTEMPTS = [
    (f"{lift}{number}", f"{column}{number}Kg")
    for lift, column in (("squat", "Squat"), ("bench", "Bench"), ("deadlift", "Deadlift"))
    for number in range(1, 5)
]


class Command(BaseCommand):
    help = "Внася международните резултати на български състезатели от OpenPowerlifting."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--country", default="Bulgaria")
        parser.add_argument("--parent-federation", default="IPF", help="празно = всички федерации")
        parser.add_argument("--abroad", action="store_true", help="само турнири извън страната")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        rows = list(self._read(options))
        if not rows:
            raise CommandError("Няма редове, които да отговарят на избора.")
        meets = {}
        for row in rows:
            meets.setdefault(self._meet_key(row), []).append(row)

        skipped = []
        self.stdout.write(f"редове: {len(rows)}   турнири: {len(meets)}")
        if options["dry_run"]:
            for key, group in sorted(meets.items())[:10]:
                self.stdout.write(f"   {key[0]}  {key[3][:50]:<50} {len(group)} реда")
            for row in rows:
                problem = self._problem(row)
                if problem:
                    skipped.append(f"{row['Name']} @ {row['MeetName']}: {problem}")
            self.stdout.write(f"без съответствие: {len(skipped)}")
            for line in skipped[:10]:
                self.stdout.write(f"   {line}")
            self.stdout.write("СУХ ПРОБЕГ, нищо не е записано.")
            return

        created_meets = created_rows = created_athletes = 0
        with transaction.atomic():
            for key, group in sorted(meets.items()):
                competition, was_new = self._competition(key)
                created_meets += int(was_new)
                competition.results.all().delete()
                for row in group:
                    problem = self._problem(row)
                    if problem:
                        skipped.append(f"{row['Name']} @ {row['MeetName']}: {problem}")
                        continue
                    athlete, is_new = athlete_for(row["Name"], row["Sex"])
                    created_athletes += int(is_new)
                    self._result(competition, athlete, row)
                    created_rows += 1
            recalculate_records()

        self.stdout.write(
            f"турнири: {created_meets} нови от {len(meets)}   "
            f"резултати: {created_rows}   нови състезатели: {created_athletes}   "
            f"пропуснати: {len(skipped)}"
        )
        for line in skipped[:20]:
            self.stdout.write(f"   пропуснат: {line}")

    def _read(self, options):
        csv.field_size_limit(10**7)
        with open(options["csv_path"], newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if options["country"] and row["Country"] != options["country"]:
                    continue
                parent = options["parent_federation"]
                if parent and row["ParentFederation"] != parent:
                    continue
                if options["abroad"] and row["MeetCountry"] == options["country"]:
                    continue
                yield row

    def _meet_key(self, row):
        return (row["Date"], row["Federation"], row["MeetCountry"], row["MeetName"], row["MeetTown"])

    def _competition(self, key):
        day, federation, country, name, town = key
        slug = f"{day}-{slugify(transliterate(f'{federation}-{name}'), allow_unicode=False)}"[:320]
        existing = Competition.objects.filter(slug=slug).first()
        if existing:
            return existing, False
        return (
            Competition.objects.create(
                slug=unique_slug(Competition, slug),
                name=name,
                start_date=date.fromisoformat(day),
                city=town,
                country=country,
                level=MeetLevel.INTERNATIONAL,
                notes=f"Федерация: {federation}. Източник: OpenPowerlifting.",
            ),
            True,
        )

    def _problem(self, row):
        if not row["Name"]:
            return "няма име"
        if row["Sex"] not in Sex.values:
            return f"пол {row['Sex']!r}"
        if row["Event"] not in EVENTS:
            return f"дисциплина {row['Event']!r}"
        if row["Equipment"] not in EQUIPMENT:
            return f"екипировка {row['Equipment']!r}"
        if not self._age_group(row):
            return f"възрастова група {row['Division']!r}"
        return ""

    def _age_group(self, row):
        found = DIVISIONS.get(row["Division"].strip().lower())
        if found:
            return found
        for label, group in BIRTH_YEAR_CLASS:
            if row["BirthYearClass"] == label:
                return group
        return ""

    def _result(self, competition, athlete, row):
        def number(column):
            value = (row.get(column) or "").strip()
            return value or None

        result = Result(
            competition=competition,
            athlete=athlete,
            raw_name=row["Name"],
            country="България",
            sex=row["Sex"],
            age_group=self._age_group(row),
            equipment=EQUIPMENT[row["Equipment"]],
            event=EVENTS[row["Event"]],
            weight_class=row["WeightClassKg"],
            bodyweight=number("BodyweightKg"),
            place=row["Place"],
            best_squat=number("Best3SquatKg"),
            best_bench=number("Best3BenchKg"),
            best_deadlift=number("Best3DeadliftKg"),
            total=number("TotalKg"),
            points=number("Goodlift") or number("Dots"),
            points_formula="IPF GL" if number("Goodlift") else "Dots",
        )
        for field_name, column in ATTEMPTS:
            setattr(result, field_name, number(column))
        result.save()
