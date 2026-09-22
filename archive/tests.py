from datetime import date
from io import BytesIO

import openpyxl
from django.test import TestCase

from archive.models import AgeGroup, Athlete, Competition, Equipment, Event, Lift, Record, RecordOrigin, Result, Sex
from archive.services.commit import apply_import
from archive.services.importers import parse_upload
from archive.services.names import athlete_name_key, transliterate
from archive.services.records import recalculate_records


class MissingProtocolTests(TestCase):
    def test_past_meet_without_file_says_there_is_no_protocol(self):
        Competition.objects.create(
            name="Без протокол",
            start_date=date(2023, 5, 27),
            city="София",
            slug="test-missing",
        )
        listing = self.client.get("/sustezaniya/")
        self.assertContains(listing, "Няма протокол")
        detail = self.client.get("/sustezaniya/test-missing/")
        self.assertContains(detail, "Няма протокол")

    def test_future_meet_is_marked_as_not_held_yet(self):
        Competition.objects.create(name="Предстои", start_date=date(2026, 11, 1), slug="test-future")
        detail = self.client.get("/sustezaniya/test-future/")
        self.assertContains(detail, "Още не е проведено")
        self.assertNotContains(detail, "Няма протокол")


class NameTests(TestCase):
    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_transliteration_and_order(self):
        self.assertEqual(transliterate("Рая Андонова"), "Raya Andonova")
        self.assertEqual(
            athlete_name_key("Рая Андонова", ""),
            athlete_name_key("", "Andonova Raya"),
        )


class ImporterTests(TestCase):
    def test_openpowerlifting_sheet(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Federation", "Date", "MeetCountry", "MeetState", "MeetTown", "MeetName", "Formula"])
        sheet.append(["БФСТ", "2026-04-03", "България", "", "Свищов", "Първи кръг", "IPF GL Points"])
        sheet.append([])
        sheet.append(
            [
                "Place",
                "Name",
                "Sex",
                "Country",
                "Division",
                "BodyweightKg",
                "WeightClassKg",
                "Squat1Kg",
                "Squat2Kg",
                "Squat3Kg",
                "Best3SquatKg",
                "Bench1Kg",
                "Bench2Kg",
                "Bench3Kg",
                "Best3BenchKg",
                "Deadlift1Kg",
                "Deadlift2Kg",
                "Deadlift3Kg",
                "Best3DeadliftKg",
                "TotalKg",
                "Points",
                "Event",
                "",
            ]
        )
        sheet.append([])
        sheet.append(
            [
                1,
                "Рая Андонова",
                "F",
                "BUL",
                "SJR",
                61.9,
                63,
                80,
                90,
                100,
                100,
                35,
                42.5,
                -45,
                42.5,
                105,
                112.5,
                122.5,
                122.5,
                265,
                58.65,
                "SBD",
                "НСА",
            ]
        )
        parsed = parse_upload("svishov.xlsx", _bytes(workbook))
        self.assertEqual(parsed.kind, "opl")
        self.assertEqual(parsed.meet_date, date(2026, 4, 3))
        self.assertEqual(parsed.city, "Свищов")
        self.assertEqual(len(parsed.rows), 1)
        row = parsed.rows[0]
        self.assertEqual(row.raw_name, "Рая Андонова")
        self.assertEqual(row.sex, Sex.F)
        self.assertEqual(row.age_group, AgeGroup.SUBJUNIOR)
        self.assertEqual(row.weight_class, "63")
        self.assertEqual(row.event, Event.SBD)
        self.assertEqual(row.best_squat, 100)
        self.assertEqual(row.attempts["bench3"], -45)
        self.assertEqual(row.best_bench, 42.5)
        self.assertEqual(row.total, 265)
        self.assertEqual(row.club, "НСА")
        self.assertEqual(row.equipment, "")

    def test_goodlift_bench_sheet(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Benchpress 2026 NSA • BG, Sofia • 30.05.2026"])
        sheet.append([])
        sheet.append([])
        sheet.append([])
        sheet.append(["PL.", "Name", "B.Date", "Nation", "Weight", "Lot", "1 Att.", "2 Att.", "3 Att.", "RESULT", "Pts."])
        sheet.append(["Subjuniors"])
        sheet.append(["- 66 kg"])
        sheet.append([1, "Karakashev Dimitar", "01.01.09", "Yunak", 66, 21, 85, 90, "X", 90, 72.631])
        parsed = parse_upload("bench.xlsx", _bytes(workbook))
        self.assertEqual(parsed.kind, "goodlift")
        self.assertEqual(parsed.meet_date, date(2026, 5, 30))
        self.assertEqual(len(parsed.rows), 1)
        row = parsed.rows[0]
        self.assertEqual(row.age_group, AgeGroup.SUBJUNIOR)
        self.assertEqual(row.weight_class, "66")
        self.assertEqual(row.event, Event.B)
        self.assertEqual(row.club, "Yunak")
        self.assertEqual(row.best_bench, 90)
        self.assertIsNone(row.attempts.get("bench3"))
        self.assertEqual(row.country, "")


class RecordTests(TestCase):
    def test_results_fill_empty_cells_and_keep_history(self):
        lifter = Athlete.objects.create(name_bg="Иван Петров", sex=Sex.M)
        other = Athlete.objects.create(name_bg="Петър Иванов", sex=Sex.M)
        Record.objects.create(
            sex=Sex.M,
            age_group=AgeGroup.OPEN,
            equipment=Equipment.CLASSIC,
            event=Event.SBD,
            lift=Lift.SQUAT,
            weight_class="93",
            value_kg=300,
            origin=RecordOrigin.STANDARD,
        )
        seed_holder = Athlete.objects.create(name_bg="Стар Рекорд", sex=Sex.M)
        seed = Record.objects.create(
            sex=Sex.M,
            age_group=AgeGroup.OPEN,
            equipment=Equipment.CLASSIC,
            event=Event.SBD,
            lift=Lift.BENCH,
            weight_class="93",
            value_kg=200,
            athlete=seed_holder,
            origin=RecordOrigin.SEED,
            valid_from=date(2019, 1, 1),
            note="БФСТ",
        )
        below = self._result(lifter, date(2024, 5, 1), best_squat=290, best_bench=190)
        above = self._result(other, date(2024, 9, 1), best_squat=310, best_bench=210)
        recalculate_records()
        self.assertFalse(Record.objects.filter(origin=RecordOrigin.RESULT, lift=Lift.SQUAT, result=below).exists())
        squat = Record.objects.get(origin=RecordOrigin.RESULT, lift=Lift.SQUAT, age_group=AgeGroup.OPEN, valid_to=None)
        self.assertEqual(squat.value_kg, 310)
        self.assertEqual(squat.athlete, other)
        seed.refresh_from_db()
        self.assertEqual(seed.valid_to, date(2024, 9, 1))
        current_bench = Record.objects.get(origin=RecordOrigin.RESULT, lift=Lift.BENCH, valid_to=None)
        self.assertEqual(current_bench.value_kg, 210)
        recalculate_records()
        self.assertEqual(Record.objects.filter(origin=RecordOrigin.RESULT, lift=Lift.SQUAT).count(), 1)

    def test_junior_also_sets_open_and_full_meet_bench_stays_separate(self):
        lifter = Athlete.objects.create(name_bg="Млад Състезател", sex=Sex.M)
        self._result(lifter, date(2024, 6, 1), age_group=AgeGroup.JUNIOR, best_squat=180, best_bench=120, best_deadlift=200, total=500)
        recalculate_records()
        self.assertTrue(Record.objects.filter(age_group=AgeGroup.JUNIOR, lift=Lift.TOTAL, value_kg=500).exists())
        self.assertTrue(Record.objects.filter(age_group=AgeGroup.OPEN, lift=Lift.TOTAL, value_kg=500).exists())
        self.assertFalse(Record.objects.filter(event=Event.B).exists())

    def test_doping_foreign_and_earlier_conflict(self):
        lifter = Athlete.objects.create(name_bg="Българин", sex=Sex.M)
        Record.objects.create(
            sex=Sex.M,
            age_group=AgeGroup.OPEN,
            equipment=Equipment.CLASSIC,
            event=Event.SBD,
            lift=Lift.DEADLIFT,
            weight_class="93",
            value_kg=300,
            athlete=lifter,
            origin=RecordOrigin.SEED,
            valid_from=date(2024, 6, 1),
        )
        early = self._result(lifter, date(2023, 1, 1), best_deadlift=310)
        self._result(lifter, date(2024, 8, 1), best_deadlift=320, place="DD")
        guest = Athlete.objects.create(name_lat="Foreign Guest", sex=Sex.M)
        self._result(guest, date(2024, 8, 2), best_deadlift=400, country="USA")
        recalculate_records()
        early.refresh_from_db()
        self.assertIn("по-ранна дата", early.review_note)
        current = Record.objects.get(lift=Lift.DEADLIFT, valid_to=None, origin=RecordOrigin.SEED)
        self.assertEqual(current.value_kg, 300)

    def test_import_creates_athlete_once(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Place", "Name", "Sex", "Country", "Division", "WeightClassKg", "Best3BenchKg", "Event"])
        sheet.append([1, "Иван Петров", "M", "BUL", "Open", "93", 150, "B"])
        parsed = parse_upload("bench.csv", b"")
        parsed = parse_upload("one.xlsx", _bytes(workbook))
        competition = Competition.objects.create(name="Лег", start_date=date(2025, 5, 1))
        summary = apply_import(
            competition,
            parsed,
            default_sex="",
            default_equipment=Equipment.CLASSIC,
            default_event="auto",
            replace=True,
        )
        self.assertEqual(summary["created"], 1)
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(Record.objects.get(event=Event.B, lift=Lift.BENCH).value_kg, 150)
        apply_import(
            competition,
            parsed,
            default_sex="",
            default_equipment=Equipment.CLASSIC,
            default_event="auto",
            replace=True,
        )
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(Result.objects.count(), 1)

    def test_photos_stay_hidden_under_18(self):
        minor = Athlete.objects.create(name_bg="Юноша", sex=Sex.M, birth_year=date.today().year - 16)
        adult = Athlete.objects.create(name_bg="Възрастен", sex=Sex.M, birth_year=date.today().year - 30)
        unknown = Athlete.objects.create(name_bg="Без година", sex=Sex.M)
        confirmed = Athlete.objects.create(name_bg="Потвърден", sex=Sex.M, adult_confirmed=True)
        self.assertFalse(minor.allows_public_photos)
        self.assertTrue(adult.allows_public_photos)
        self.assertFalse(unknown.allows_public_photos)
        self.assertTrue(confirmed.allows_public_photos)

    def _result(self, athlete, day, **fields):
        competition = Competition.objects.create(name=f"Турнир {day.isoformat()}", start_date=day)
        defaults = {
            "sex": athlete.sex,
            "age_group": AgeGroup.OPEN,
            "equipment": Equipment.CLASSIC,
            "event": Event.SBD,
            "weight_class": "93",
            "country": "България",
            "raw_name": athlete.display_name,
        }
        defaults.update(fields)
        return Result.objects.create(competition=competition, athlete=athlete, **defaults)


def _bytes(workbook):
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
