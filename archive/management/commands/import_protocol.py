"""Load a federation protocol from the command line.

The same path as the /import/ page, for loading the back catalogue without
clicking through it once per meet.
"""

from io import BytesIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from archive.models import Competition, FileKind
from archive.services.commit import (
    KEEP, REPLACE_ALL, REPLACE_FILE, ReplaceScopeError, apply_import, matching_source,
    prepare_rows, rows_to_replace,
)
from archive.services.importers import parse_upload


class Command(BaseCommand):
    help = "Внася протокол (.xlsx/.xlsm/.csv) в съществуващо състезание."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--competition", required=True, help="slug на състезанието")
        parser.add_argument("--sex", default="", choices=["", "M", "F"])
        parser.add_argument("--equipment", default="auto", choices=["auto", "classic", "equipped"])
        parser.add_argument("--event", default="auto", choices=["auto", "SBD", "B", "D", "PP"])
        parser.add_argument("--age-group", default="", dest="age_group",
                            choices=["", "subjunior", "junior", "open", "m1", "m2", "m3", "m4"],
                            help="за протокол без възрастови секции")
        scope = parser.add_mutually_exclusive_group()
        scope.add_argument("--keep", action="store_true", help="добавя, вместо да замени")
        scope.add_argument("--replace-all", action="store_true", dest="replace_all",
                           help="трие всички редове на турнира, не само тези от същия файл")
        parser.add_argument("--reclass", action="store_true",
                            help="изчислява категориите по теглото — за протокол, "
                                 "писан по остарял набор категории")
        parser.add_argument("--attach", action="store_true",
                            help="закача файла към турнира като източник")
        parser.add_argument("--title", default="",
                            help="как да се изписва закаченият файл на страницата")
        parser.add_argument("--skip-blocked", action="store_true", help="внася въпреки спрените редове")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            competition = Competition.objects.get(slug=options["competition"])
        except Competition.DoesNotExist:
            raise CommandError(f"Няма състезание със slug {options['competition']!r}.")

        with open(options["path"], "rb") as handle:
            payload = handle.read()
        parsed = parse_upload(options["path"], payload)
        if not parsed.rows:
            raise CommandError(" ".join(parsed.errors) or "Файлът няма редове за внасяне.")

        defaults = {
            "default_sex": options["sex"],
            "default_equipment": options["equipment"],
            "default_event": options["event"],
            "default_age_group": options["age_group"],
            "reclass": options["reclass"],
        }
        ready, blocked = prepare_rows(
            parsed, meet_level=competition.level, meet_date=competition.start_date, **defaults
        )
        self.stdout.write(
            f"{competition.name} ({competition.start_date})\n"
            f"  прочетени: {len(parsed.rows)}   отсети: {parsed.skipped}   "
            f"дублирани: {parsed.duplicates}\n"
            f"  готови: {len(ready)}   спрени: {len(blocked)}"
        )
        for item in blocked[:8]:
            self.stdout.write(f"     спрян ред {item['row']} {item['name']}: {'; '.join(item['problems'])}")
        if blocked and len(blocked) > 8:
            self.stdout.write(f"     … и още {len(blocked) - 8}")

        if blocked and not options["skip_blocked"]:
            raise CommandError(
                "Има спрени редове. Оправи ги или подай --skip-blocked, за да внесеш останалите."
            )
        mode = KEEP if options["keep"] else REPLACE_ALL if options["replace_all"] else REPLACE_FILE
        filename = Path(options["path"]).name if options["attach"] else ""
        try:
            doomed = rows_to_replace(
                competition, matching_source(competition, filename), mode,
                keeps_file=options["attach"],
            )
        except ReplaceScopeError as error:
            raise CommandError(str(error))
        self.stdout.write(f"  заменят се: {doomed.count()} от {competition.results.count()} реда")
        if options["dry_run"]:
            self.stdout.write("СУХ ПРОБЕГ, нищо не е записано.")
            return

        if options["skip_blocked"] and blocked:
            parsed.rows = ready
        if not options["keep"]:
            # The protocol is the source now, so a note pointing at
            # OpenPowerlifting for these rows would be wrong.
            dropped = competition.files.filter(kind=FileKind.OPL).delete()[0]
            if dropped:
                self.stdout.write(f"  махнат източник OpenPowerlifting: {dropped}")
        stored = BytesIO(payload) if options["attach"] else None
        summary = apply_import(
            competition, parsed, replace=mode, stored_file=stored, filename=filename,
            title=options["title"], **defaults
        )
        self.stdout.write(
            f"  записани: {summary['created']}   нови състезатели: {summary['athletes']}"
        )
