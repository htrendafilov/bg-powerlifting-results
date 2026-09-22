import re
from collections import Counter
from datetime import date
from io import BytesIO
from pathlib import Path

import openpyxl
from django.test import TestCase, override_settings

from archive.models import (
    AgeGroup, Athlete, Competition, Equipment, Event, Lift, MeetLevel, Record,
    RecordOrigin, Result, Sex,
)
from archive.services.commit import apply_import, prepare_rows
from archive.services.importers import _equipment_in_text, parse_upload
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
        listing = self.client.get("/competitions/")
        self.assertContains(listing, "Няма протокол")
        detail = self.client.get("/competitions/test-missing/")
        self.assertContains(detail, "Няма протокол")

    def test_future_meet_is_marked_as_not_held_yet(self):
        Competition.objects.create(name="Предстои", start_date=date(2026, 11, 1), slug="test-future")
        detail = self.client.get("/competitions/test-future/")
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


class RealProtocolTests(TestCase):
    """The two protocol shapes the federation actually publishes. Synthetic
    sheets missed every defect these files carry."""

    def _fixture(self, name):
        return (Path(__file__).parent / "tests_data" / name).read_bytes()

    def test_goodlift_bench_drops_team_and_best_lifter_tables(self):
        parsed = parse_upload("bench.xlsx", self._fixture("goodlift_bench_2026.xlsx"))
        self.assertEqual(parsed.kind, "goodlift")
        self.assertEqual(len(parsed.rows), 85)
        self.assertEqual(parsed.skipped, 57)
        self.assertIn("Nation (points)", parsed.skipped_sections)
        names = {row.raw_name for row in parsed.rows}
        for club in ("MNG", "NSA-Sofia", "STRONG", "Marek-13"):
            self.assertNotIn(club, names)

    def test_goodlift_seniors_are_not_filed_as_juniors(self):
        parsed = parse_upload("bench.xlsx", self._fixture("goodlift_bench_2026.xlsx"))
        by_group = Counter(row.age_group for row in parsed.rows)
        self.assertEqual(by_group[AgeGroup.OPEN], 31)
        self.assertEqual(by_group[AgeGroup.JUNIOR], 20)

    def test_goodlift_nation_column_of_a_domestic_meet_is_the_club(self):
        parsed = parse_upload("bench.xlsx", self._fixture("goodlift_bench_2026.xlsx"))
        self.assertEqual({row.country for row in parsed.rows}, {""})
        self.assertEqual(parsed.rows[0].club, "Yunak")

    def test_goodlift_bench_needs_an_equipment_choice(self):
        parsed = parse_upload("bench.xlsx", self._fixture("goodlift_bench_2026.xlsx"))
        _, blocked = prepare_rows(parsed, default_sex=Sex.M, default_equipment="auto", default_event="auto")
        self.assertEqual(len(blocked), 85)
        self.assertIn("Няма екипировка", blocked[0]["problems"][0])
        ready, blocked = prepare_rows(
            parsed, default_sex=Sex.M, default_equipment=Equipment.CLASSIC, default_event="auto"
        )
        self.assertEqual((len(ready), len(blocked)), (85, 0))

    def test_opl_sbd_protocol_still_imports_whole(self):
        parsed = parse_upload("svishtov.xlsx", self._fixture("opl_sbd_2026.xlsx"))
        self.assertEqual(parsed.kind, "opl")
        self.assertEqual(len(parsed.rows), 146)
        self.assertEqual(parsed.skipped, 0)
        self.assertEqual(parsed.meet_date, date(2026, 4, 3))
        self.assertEqual(parsed.city, "Свищов")
        by_group = Counter(row.age_group for row in parsed.rows)
        self.assertEqual(by_group[AgeGroup.OPEN], 61)
        # "с екип" in the meet title, so the title supplies it and the operator need not.
        self.assertEqual({row.equipment for row in parsed.rows}, {Equipment.EQUIPPED})


class GoodliftFullPowerTests(TestCase):
    def _sheet(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Powerlifting 2026 • BG, Sofia • 19.09.2026"])
        sheet.append([])
        sheet.append([
            "PL.", "Name", "B.Date", "Nation", "Weight", "Lot",
            "1 Att.", "2 Att.", "3 Att.",
            "1 Att.", "2 Att.", "3 Att.",
            "1 Att.", "2 Att.", "3 Att.",
            "RESULT", "Pts.",
        ])
        sheet.append(["Seniors"])
        sheet.append(["- 93 kg"])
        sheet.append([1, "Ivanov Ivan", "01.01.95", "Levski", 92.5, 7,
                      250, 260, 270, 150, 160, "X", 280, 290, 300, 730, 90.1])
        return _bytes(workbook)

    def test_three_attempt_blocks_land_on_the_right_lifts(self):
        row = parse_upload("full.xlsx", self._sheet()).rows[0]
        self.assertEqual(row.event, Event.SBD)
        self.assertEqual(row.age_group, AgeGroup.OPEN)
        self.assertEqual(row.attempts["squat3"], 270)
        self.assertEqual(row.attempts["bench2"], 160)
        self.assertEqual(row.attempts["deadlift3"], 300)
        self.assertEqual((row.best_squat, row.best_bench, row.best_deadlift), (270, 160, 300))
        self.assertEqual(row.total, 730)

    def test_an_unknown_attempt_layout_is_refused_not_guessed(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["PL.", "Name", "1 Att.", "2 Att.", "3 Att.", "1 Att.", "2 Att.", "3 Att.", "RESULT"])
        sheet.append(["Open"])
        sheet.append(["- 93 kg"])
        sheet.append([1, "Ivanov Ivan", 100, 110, 120, 130, 140, 150, 270])
        row = parse_upload("odd.xlsx", _bytes(workbook)).rows[0]
        self.assertTrue(any("Неразпознат Goodlift лист" in problem for problem in row.errors))


class ForeignLifterTests(TestCase):
    def _euro_sheet(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["European Bench Press Championships • Kaunas • 12.05.2026"])
        sheet.append([])
        sheet.append(["PL.", "Name", "B.Date", "Nation", "Weight", "Lot", "1 Att.", "2 Att.", "3 Att.", "RESULT", "Pts."])
        sheet.append(["Seniors"])
        sheet.append(["- 83 kg"])
        sheet.append([1, "Petrauskas Jonas", "01.01.95", "LTU", 82.5, 3, 200, 210, 220, 220, 130.0])
        sheet.append([2, "Kovacs Andras", "01.01.95", "HUN", 82.7, 5, 195, 205, 215, 215, 127.0])
        sheet.append([3, "Ivanov Ivan", "01.01.95", "BUL", 82.9, 4, 190, 200, "X", 200, 120.0])
        return _bytes(workbook)

    def test_nation_column_of_an_international_meet_is_the_country(self):
        parsed = parse_upload("euro.xlsx", self._euro_sheet())
        self.assertEqual([row.country for row in parsed.rows], ["LTU", "HUN", "BUL"])
        self.assertEqual({row.club for row in parsed.rows}, {""})

    def test_foreigners_do_not_take_bulgarian_records(self):
        parsed = parse_upload("euro.xlsx", self._euro_sheet())
        competition = Competition.objects.create(
            name="Европейско", start_date=date(2026, 5, 12), level=MeetLevel.INTERNATIONAL
        )
        apply_import(
            competition, parsed, default_sex=Sex.M, default_equipment=Equipment.CLASSIC,
            default_event="auto", replace=True,
        )
        self.assertEqual(Result.objects.count(), 3)
        holder = Record.objects.get(origin=RecordOrigin.RESULT, lift=Lift.BENCH, valid_to=None)
        self.assertEqual(holder.value_kg, 200)
        self.assertEqual(holder.athlete.name_lat, "Ivanov Ivan")

    def test_an_international_row_without_a_country_is_blocked(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Place", "Name", "Sex", "Division", "WeightClassKg", "Best3BenchKg", "Event"])
        sheet.append([1, "Ivanov Ivan", "M", "Open", "93", 150, "B"])
        parsed = parse_upload("nc.xlsx", _bytes(workbook))
        _, blocked = prepare_rows(
            parsed, default_sex="", default_equipment=Equipment.CLASSIC, default_event="auto",
            meet_level=MeetLevel.INTERNATIONAL,
        )
        self.assertIn("Няма държава", blocked[0]["problems"][0])


class MeetTitleEquipmentTests(TestCase):
    def test_combined_rounds_do_not_claim_to_be_raw(self):
        self.assertEqual(_equipment_in_text("2 кръг, вдигане от лег с и без екип"), "")
        self.assertEqual(_equipment_in_text("Силов трибой с и без екип"), "")
        self.assertEqual(_equipment_in_text("3 кръг, силов трибой без екип"), Equipment.CLASSIC)
        self.assertEqual(_equipment_in_text("Класически силов трибой"), Equipment.CLASSIC)
        self.assertEqual(_equipment_in_text("2 кръг, силов трибой с екип"), Equipment.EQUIPPED)
        self.assertEqual(_equipment_in_text("Екипировъчен силов трибой"), Equipment.EQUIPPED)

    def test_the_operator_overrides_the_title_but_not_a_column(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["MeetName", "Силов трибой без екип"])
        sheet.append([])
        sheet.append(["Place", "Name", "Sex", "Country", "Division", "WeightClassKg", "Best3BenchKg", "Event"])
        sheet.append([1, "Ivan Ivanov", "M", "BUL", "Open", "93", 150, "B"])
        parsed = parse_upload("t.xlsx", _bytes(workbook))
        self.assertEqual(parsed.rows[0].equipment_source, "title")
        ready, _ = prepare_rows(
            parsed, default_sex="", default_equipment=Equipment.EQUIPPED, default_event="auto"
        )
        self.assertEqual(ready[0].equipment, Equipment.EQUIPPED)


class UrlTests(TestCase):
    def test_english_paths_answer_and_old_ones_redirect(self):
        Competition.objects.create(name="Турнир", start_date=date(2025, 5, 1), slug="t")
        for path in ("/competitions/", "/records/", "/athletes/", "/competitions/t/"):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        for old, new in (
            ("/sustezaniya/", "/competitions/"),
            ("/sustezaniya/t/", "/competitions/t/"),
            ("/rekordi/", "/records/"),
            ("/sastezateli/", "/athletes/"),
        ):
            response = self.client.get(old)
            self.assertEqual(response.status_code, 302, old)
            self.assertEqual(response["Location"], new)

    def test_redirect_keeps_the_query_string(self):
        response = self.client.get("/rekordi/?sex=F&event=B")
        self.assertEqual(response["Location"], "/records/?sex=F&event=B")


class OrderingTests(TestCase):
    def test_competitions_are_listed_newest_first_despite_the_annotation(self):
        for day, name, slug in (
            (date(2021, 6, 5), "стар", "old"),
            (date(2026, 4, 3), "нов", "new"),
            (date(2023, 7, 1), "среден", "mid"),
        ):
            Competition.objects.create(name=name, start_date=day, slug=slug)
        home = self.client.get("/")
        listing = self.client.get("/competitions/")
        for page in (home, listing):
            body = page.content.decode()
            order = [body.index(f"/competitions/{slug}/") for slug in ("new", "mid", "old")]
            self.assertEqual(order, sorted(order), page.request["PATH_INFO"])
        years = [int(y) for y in re.findall(r"<h2>(\d{4})</h2>", listing.content.decode())]
        self.assertEqual(years, sorted(years, reverse=True))


class DeadliftOnlyTests(TestCase):
    def test_a_deadlift_sheet_is_not_recorded_as_bench(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Национален шампионат по мъртва тяга • София • 26.11.2026"])
        sheet.append([])
        sheet.append(["PL.", "Name", "Nation", "Weight", "1 Att.", "2 Att.", "3 Att.", "RESULT", "Pts."])
        sheet.append(["Seniors"])
        sheet.append(["- 93 kg"])
        sheet.append([1, "Ivanov Ivan", "Levski", 92.5, 250, 265, 280, 280, 90.1])
        row = parse_upload("dl.xlsx", _bytes(workbook)).rows[0]
        self.assertEqual(row.event, Event.D)
        self.assertEqual(row.best_deadlift, 280)
        self.assertIsNone(row.best_bench)
        self.assertEqual(row.attempts["deadlift3"], 280)
        self.assertNotIn("bench1", row.attempts)

    def test_a_deadlift_result_never_becomes_a_record(self):
        athlete = Athlete.objects.create(name_bg="Тягаджия", sex=Sex.M)
        competition = Competition.objects.create(name="Тяга", start_date=date(2026, 11, 26))
        Result.objects.create(
            competition=competition, athlete=athlete, sex=Sex.M, age_group=AgeGroup.OPEN,
            equipment=Equipment.CLASSIC, event=Event.D, weight_class="93",
            country="България", best_deadlift=400,
        )
        recalculate_records()
        self.assertEqual(Record.objects.count(), 0)

    def test_a_meet_can_be_excluded_from_records_by_hand(self):
        athlete = Athlete.objects.create(name_bg="Показен", sex=Sex.M)
        competition = Competition.objects.create(name="Показен", start_date=date(2026, 3, 1))
        result = Result.objects.create(
            competition=competition, athlete=athlete, sex=Sex.M, age_group=AgeGroup.OPEN,
            equipment=Equipment.CLASSIC, event=Event.SBD, weight_class="93",
            country="България", best_bench=250, counts_for_records=False,
        )
        recalculate_records()
        self.assertEqual(Record.objects.count(), 0)
        result.counts_for_records = True
        result.save()
        recalculate_records()
        self.assertEqual(Record.objects.filter(lift=Lift.BENCH, value_kg=250).count(), 1)


@override_settings(
    DEBUG=False, SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=31536000,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True, SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)
class HttpsTests(TestCase):
    def test_plain_http_is_redirected(self):
        response = self.client.get("/competitions/")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_a_request_behind_the_tunnel_is_served_with_hsts(self):
        response = self.client.get("/competitions/", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(response.status_code, 200)
        self.assertIn("max-age=31536000", response["Strict-Transport-Security"])
        self.assertIn("includeSubDomains", response["Strict-Transport-Security"])


class SectionHeadingTests(TestCase):
    """A sheet whose rows carry their own Division must not lose them to a
    heading the label parser cannot read (real file: Кърджали 2023)."""

    def test_decorative_headings_do_not_swallow_the_rows(self):
        data = (Path(__file__).parent / "tests_data" / "opl_sections_2023.xlsx").read_bytes()
        parsed = parse_upload("k.xlsx", data)
        self.assertEqual(len(parsed.rows), 87)
        self.assertEqual(parsed.skipped, 0)

    def test_a_context_dependent_sheet_still_drops_unknown_blocks(self):
        data = (Path(__file__).parent / "tests_data" / "goodlift_bench_2026.xlsx").read_bytes()
        parsed = parse_upload("b.xlsx", data)
        self.assertEqual(parsed.skipped, 57)


class BulgarianProtocolTests(TestCase):
    """The shape the federation publishes most often: a Bulgarian header row."""

    def _fixture(self, name):
        return (Path(__file__).parent / "tests_data" / name).read_bytes()

    def test_bulgarian_headers_are_read(self):
        parsed = parse_upload("sofia.xlsx", self._fixture("bg_sbd_2024.xlsx"))
        self.assertEqual(len(parsed.rows), 170)
        ready, blocked = prepare_rows(
            parsed, default_sex="", default_equipment="auto", default_event="auto"
        )
        self.assertEqual((len(ready), len(blocked)), (170, 0))
        row = parsed.rows[0]
        self.assertTrue(row.raw_name)
        self.assertTrue(row.club)
        self.assertEqual(row.event, Event.SBD)

    def test_a_combined_division_code_supplies_sex_equipment_and_event(self):
        parsed = parse_upload("sofia.xlsx", self._fixture("bg_sbd_2024.xlsx"))
        by_sex = Counter(row.sex for row in parsed.rows)
        self.assertEqual(by_sex[Sex.F], 34)
        self.assertEqual(by_sex[Sex.M], 136)
        self.assertEqual({row.equipment for row in parsed.rows}, {Equipment.CLASSIC})
        self.assertEqual({row.equipment_source for row in parsed.rows}, {"row"})

    def test_a_deadlift_meet_is_imported_but_sets_no_record(self):
        parsed = parse_upload("dl.xlsx", self._fixture("bg_deadlift_2023.xlsx"))
        self.assertEqual({row.event for row in parsed.rows}, {Event.D})
        ready, _ = prepare_rows(
            parsed, default_sex="", default_equipment="auto", default_event="auto"
        )
        competition = Competition.objects.create(
            name="Мъртва тяга", start_date=date(2023, 11, 26), slug="dl-2023"
        )
        summary = apply_import(
            competition, parsed, default_sex="", default_equipment="auto",
            default_event="auto", replace=True,
        )
        self.assertEqual(summary["created"], 0)  # blocked rows stop the whole import
        self.assertGreater(len(ready), 60)
        self.assertEqual(Record.objects.count(), 0)


class MergedDivisionCodeTests(TestCase):
    def test_sex_prefixed_divisions_are_understood(self):
        from archive.services.importers import _division_label

        self.assertEqual(_division_label("F-Jr"), AgeGroup.JUNIOR)
        self.assertEqual(_division_label("M-O"), AgeGroup.OPEN)
        self.assertEqual(_division_label("M-T3"), AgeGroup.SUBJUNIOR)
        self.assertEqual(_division_label("M-M1"), AgeGroup.M1)
        self.assertEqual(_division_label("M1"), AgeGroup.M1)
