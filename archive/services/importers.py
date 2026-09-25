import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

import openpyxl

from archive.models import AgeGroup, Equipment, Event, Sex

_HEADER_ALIASES = {
    "place": "place",
    "pl": "place",
    "name": "name",
    "sex": "sex",
    "country": "country",
    "division": "division",
    "bodyweightkg": "bodyweight",
    "weightclasskg": "weight_class",
    "squat1kg": "squat1",
    "squat2kg": "squat2",
    "squat3kg": "squat3",
    "squat4kg": "squat4",
    "bench1kg": "bench1",
    "bench2kg": "bench2",
    "bench3kg": "bench3",
    "bench4kg": "bench4",
    "deadlift1kg": "deadlift1",
    "deadlift2kg": "deadlift2",
    "deadlift3kg": "deadlift3",
    "deadlift4kg": "deadlift4",
    "best3squatkg": "best_squat",
    "best3benchkg": "best_bench",
    "best3deadliftkg": "best_deadlift",
    "totalkg": "total",
    "points": "points",
    "pts": "points",
    "goodlift": "points",
    "event": "event",
    "club": "club",
    "team": "club",
    "equipment": "equipment",
    "1att": "att1",
    "2att": "att2",
    "3att": "att3",
    "4att": "att4",
    "result": "result",
    "weight": "bodyweight",
    "lot": "lot",
    "nation": "nation",
    # Bulgarian protocols. The federation's spelling drifts between meets, so
    # every variant seen in the published files is listed rather than guessed.
    "място": "place",
    "класиране": "place",
    "no": "place",
    "клас": "rank",
    "име": "name",
    "имеифамилия": "name",
    "фамилия": "surname",
    "пол": "sex",
    "възраст": "age",
    "гр": "age",
    "години": "age",
    "отбор": "club",
    "клуб": "club",
    "дивизия": "division",
    "група": "division",
    "възрастовагрупа": "division",
    "екипировка": "equipment",
    "тегло": "bodyweight",
    "личнотегло": "bodyweight",
    "теглокг": "bodyweight",
    "категория": "weight_class",
    "категориякг": "weight_class",
    "теглкат": "weight_class",
    "кат": "weight_class",
    "клек1": "squat1",
    "клек2": "squat2",
    "клек3": "squat3",
    "клек": "best_squat",
    "найдобрклек": "best_squat",
    "найдобклек": "best_squat",
    "найдобърклек": "best_squat",
    "лег1": "bench1",
    "лег2": "bench2",
    "лег3": "bench3",
    "лег": "best_bench",
    "найдобрлег": "best_bench",
    "найдоблег": "best_bench",
    "найдобърлег": "best_bench",
    "тяга1": "deadlift1",
    "тяга2": "deadlift2",
    "тяга3": "deadlift3",
    "мтяга1": "deadlift1",
    "мтяга2": "deadlift2",
    "мтяга3": "deadlift3",
    "тяга1виопит": "deadlift1",
    "тяга2риопит": "deadlift2",
    "тяга3тиопит": "deadlift3",
    "тяга": "best_deadlift",
    "найдобрамтяга": "best_deadlift",
    "найдобмтяга": "best_deadlift",
    "найдобратяга": "best_deadlift",
    "найдобърмтяга": "best_deadlift",
    "найдобратягa": "best_deadlift",
    "тотал": "total",
    "тоталкг": "total",
    "трибой": "total",
    "точки": "points",
    "glточки": "points",
    "ipfglточки": "points",
}


@dataclass
class ParsedRow:
    place: str = ""
    raw_name: str = ""
    sex: str = ""
    country: str = ""
    age_group: str = ""
    equipment: str = ""
    equipment_source: str = ""
    event: str = ""
    weight_class: str = ""
    bodyweight: Decimal | None = None
    age: Decimal | None = None
    club: str = ""
    nation_raw: str = ""
    lot: str = ""
    attempts: dict = field(default_factory=dict)
    best_squat: Decimal | None = None
    best_bench: Decimal | None = None
    best_deadlift: Decimal | None = None
    total: Decimal | None = None
    points: Decimal | None = None
    points_formula: str = ""
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def sex_label(self):
        return dict(Sex.choices).get(self.sex, "—")

    @property
    def age_label(self):
        return dict(AgeGroup.choices).get(self.age_group, "—")

    @property
    def equipment_label(self):
        return dict(Equipment.choices).get(self.equipment, "—")

    @property
    def event_label(self):
        return dict(Event.choices).get(self.event, "—")


@dataclass
class ParsedFile:
    kind: str
    title: str = ""
    meet_date: date | None = None
    city: str = ""
    formula: str = ""
    rows: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    skipped: int = 0
    skipped_sections: list = field(default_factory=list)
    duplicates: int = 0


@dataclass
class HeaderLayout:
    """Where each column sits. Attempt columns repeat once per lift in Goodlift
    sheets, so they are kept as an ordered list instead of a name->index map."""

    mapping: dict = field(default_factory=dict)
    attempts: list = field(default_factory=list)
    results: list = field(default_factory=list)
    divisions: list = field(default_factory=list)
    places: list = field(default_factory=list)
    total_rank: int | None = None


def parse_upload(filename, payload):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = payload.decode("utf-8-sig", errors="replace")
        rows = list(csv.reader(StringIO(text)))
        return _parse_table("Файл", rows)
    # openpyxl reads a macro-enabled workbook exactly like a plain one, and the
    # federation publishes some protocols as .xlsm.
    if name.endswith((".xlsx", ".xlsm")):
        workbook = openpyxl.load_workbook(BytesIO(payload), data_only=True, read_only=True)
        parsed_sheets = []
        for sheet in workbook.worksheets:
            table = [_clean_row(row) for row in sheet.iter_rows(values_only=True)]
            parsed = _parse_table(sheet.title, table)
            if parsed.rows:
                parsed_sheets.append(parsed)
        if not parsed_sheets:
            return ParsedFile(kind="", errors=["Файлът не е протокол от Goodlift или таблица с колони Place/Name."])
        merged = parsed_sheets[0]
        for extra in parsed_sheets[1:]:
            merged.rows.extend(extra.rows)
            merged.errors.extend(extra.errors)
            merged.skipped += extra.skipped
            for label in extra.skipped_sections:
                if label not in merged.skipped_sections:
                    merged.skipped_sections.append(label)
        merged.duplicates = _drop_duplicate_rows(merged.rows)
        return merged
    return ParsedFile(kind="", errors=["Приемат се .xlsx, .xlsm и .csv. Стар .xls се качва като файл към турнира и се нанася отделно."])


# Workbooks often keep the same protocol on several sheets ("protokol" and
# "protokol (2)", "Scoresheet" and "Scoresheet (2)"). The same lifter in two
# divisions is legitimate, so the division is part of what makes a row distinct.
def _drop_duplicate_rows(rows):
    seen = set()
    kept = []
    for item in rows:
        key = (
            item.raw_name.strip().lower(),
            item.sex,
            item.age_group,
            item.equipment,
            item.event,
            item.weight_class,
            item.best_squat,
            item.best_bench,
            item.best_deadlift,
            item.total,
        )
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    dropped = len(rows) - len(kept)
    rows[:] = kept
    return dropped


def _clean_row(row):
    cleaned = []
    for value in row:
        if value is None:
            cleaned.append("")
        elif isinstance(value, datetime):
            cleaned.append(value.date().isoformat())
        elif isinstance(value, date):
            cleaned.append(value.isoformat())
        elif isinstance(value, float):
            cleaned.append(str(int(value)) if value.is_integer() else str(value))
        elif isinstance(value, int):
            cleaned.append(str(value))
        else:
            cleaned.append(str(value).strip().lstrip("'"))
    return cleaned


def _parse_table(title, rows):
    header_index, layout = _find_header(rows)
    if header_index is None:
        return ParsedFile(kind="")
    mapping = layout.mapping
    _choose_place_column(layout, rows[header_index + 1 :])
    kind = "goodlift" if layout.attempts else "opl"
    meta = _metadata(rows[:header_index])
    blob = " ".join(cell for row in rows[: header_index + 1] for cell in row if cell)
    parsed = ParsedFile(
        kind=kind,
        title=meta.get("title") or title,
        meet_date=_parse_date(meta.get("date", "")) or _date_in_text(blob),
        city=meta.get("city", ""),
        formula=meta.get("formula", ""),
    )
    division = ""
    sex = ""
    weight_class = ""
    # Goodlift sheets interleave the results with team-score and best-lifter
    # tables that also carry a rank and a name. An unrecognised single-cell
    # heading starts such a block, so rows are dropped until the next heading
    # that names a division, a sex or a weight class.
    ignoring = False
    # Dropping a block is only safe when the rows need the heading to be read at
    # all. A sheet carrying its own Division column does not: there the headings
    # are decoration and an unknown one must not take the rows with it.
    rows_carry_division = bool(layout.divisions)
    # Same for the class: where every row states its own, an empty cell means
    # the lifter had no class — she missed the limit and lifted out of the
    # standings — not that the last heading still applies.
    rows_carry_class = "weight_class" in mapping.values()
    sheet_event = _event_from_columns(mapping) if kind == "opl" else ""
    title_equipment = _equipment_in_text(blob)
    # Workbooks are often split into a sheet per sex or per equipment ("жени",
    # "мъже без екип"). That names the rows, so it outranks the meet title and
    # the operator, exactly as a per-row column would.
    sheet_sex = _sex_in_text(title)
    sheet_equipment = _equipment_in_text(title)
    deadlift_only = len(layout.attempts) in {3, 4} and _mentions_deadlift(blob)
    for row in rows[header_index + 1 :]:
        if not any(row):
            continue
        # A row with a single filled cell is never a result: a result has a
        # name. Weight-class headings like "47.0" would otherwise read as a rank.
        label = _single_label(row)
        if label:
            found_sex = _sex_label(label)
            found_class = normalize_weight_class(label)
            found_division = _division_label(label)
            if found_sex and not found_division:
                sex = found_sex
                ignoring = False
                continue
            if found_class and _looks_like_class_label(label):
                weight_class = found_class
                ignoring = False
                continue
            if found_division:
                division = found_division
                weight_class = ""
                ignoring = False
                continue
            if not _is_place(label):
                ignoring = label if not rows_carry_division else False
            continue
        rank = layout.total_rank
        if (
            rank is not None
            and not _cell(row, rank)
            and layout.places
            and _is_place(_cell(row, layout.places[0]))
            and _mapped(row, mapping, "bodyweight")
        ):
            # A lifter who weighed in and bombed out has no placing, only a
            # start number; one who never weighed in did not show up.
            row = _with_cell(row, rank, "DQ")
        # The judges write the status where the total would be ("DSQ"), and it
        # outranks whatever the place column still holds — even an empty one.
        status = _total_status(_mapped(row, mapping, "total"))
        if status:
            row = _with_cell(row, _index_of(mapping, "place"), status)
        if not _is_place(_mapped(row, mapping, "place")):
            continue
        if ignoring:
            parsed.skipped += 1
            if ignoring not in parsed.skipped_sections:
                parsed.skipped_sections.append(ignoring)
            continue
        item = _row_from_mapping(row, mapping, layout, kind)
        # A row that could not be read at all is reported, not dropped.
        if not item.errors and not _is_result_row(item):
            parsed.skipped += 1
            continue
        item.age_group = item.age_group or division
        item.event = item.event or sheet_event
        item.sex = item.sex or sex or sheet_sex
        if not rows_carry_class:
            item.weight_class = item.weight_class or weight_class
        if not item.equipment and sheet_equipment:
            item.equipment = sheet_equipment
            item.equipment_source = "sheet"
        if not item.equipment and title_equipment:
            item.equipment = title_equipment
            item.equipment_source = "title"
        item.points_formula = parsed.formula
        # The attempt-column count already decided the lifts; the title is only
        # consulted for the one case it cannot tell apart from a bench sheet.
        if deadlift_only:
            item.attempts = {
                key.replace("bench", "deadlift"): value for key, value in item.attempts.items()
            }
            item.best_deadlift, item.best_bench = item.best_bench, None
            item.event = Event.D
        if not item.raw_name:
            item.errors.append("Липсва име.")
        parsed.rows.append(item)
    _assign_nation(parsed.rows)
    _assign_age_codes(parsed.rows)
    if not parsed.rows:
        parsed.errors.append(f"{title}: разпознат е заглавен ред, но няма стартове.")
    return parsed


# The federation's "ГР" column holds either the lowest age of the division (18,
# 23, 24, 40, 70) or an ordinal code, and only the ordinal scheme reaches below
# five, so the whole column decides which of the two it is.
_ORDINAL_AGE_CODES = {
    0: AgeGroup.OPEN,
    1: AgeGroup.M1,
    2: AgeGroup.M2,
    3: AgeGroup.M3,
    4: AgeGroup.M4,
    18: AgeGroup.SUBJUNIOR,
    23: AgeGroup.JUNIOR,
}


def _assign_age_codes(rows):
    values = [int(row.age) for row in rows if row.age is not None]
    if not any(value <= 4 for value in values):
        return
    for row in rows:
        if row.age is None:
            continue
        row.age_group = row.age_group or _ORDINAL_AGE_CODES.get(int(row.age), "")
        row.age = None

# A Goodlift "Nation" column holds country codes at an international meet and
# club names at a domestic one, so the whole column decides, not a single row.
def _assign_nation(rows):
    values = [row.nation_raw.strip() for row in rows if row.nation_raw.strip()]
    holds_countries = len(set(values)) >= 3 and all(
        re.fullmatch(r"[A-Z]{3}", value) for value in values
    )
    for row in rows:
        value = row.nation_raw.strip()
        if not value:
            continue
        if holds_countries:
            row.country = row.country or value
        elif not row.club:
            row.club = value


def _find_header(rows):
    for index, row in enumerate(rows[:40]):
        normalized = [_norm_header(cell) for cell in row]
        fields = {_HEADER_ALIASES.get(cell) for cell in normalized}
        if "place" not in fields:
            continue
        layout = _header_layout(normalized)
        if "name" in fields:
            return index, layout
        # Some protocols leave the heading above the names empty. Accept the
        # column next to the rank, but only in a row that is clearly a header.
        if len(layout.mapping) < 4:
            continue
        # The place column sits in layout.places until _choose_place_column moves
        # it into mapping, which happens after this function returns.
        place_index = layout.places[0]
        candidate = place_index + 1
        if candidate < len(normalized) and not normalized[candidate] and candidate not in layout.mapping:
            layout.mapping[candidate] = "name"
            return index, layout
    return None, HeaderLayout()


def _choose_place_column(layout, body):
    """Some protocols head both the running number and the placing "№".

    The placing starts again at 1 in every class, so it repeats; the running
    number is unique down the whole sheet. That is what tells them apart.
    """
    if layout.total_rank is not None:
        layout.mapping[layout.total_rank] = "place"
        return
    if not layout.places:
        return
    chosen = layout.places[0]
    if len(layout.places) > 1:
        def repeats(index):
            values = [_cell(row, index).strip() for row in body]
            values = [v for v in values if v and _is_place(v)]
            return len(set(values)) if values else 10**6

        chosen = min(layout.places, key=repeats)
    layout.mapping[chosen] = "place"


def _header_layout(normalized):
    layout = HeaderLayout()
    for index, header in enumerate(normalized):
        field_name = _HEADER_ALIASES.get(header)
        if not field_name:
            continue
        if field_name in {"att1", "att2", "att3", "att4"}:
            layout.attempts.append(index)
            continue
        if field_name == "result":
            layout.results.append(index)
            continue
        if field_name == "division":
            layout.divisions.append(index)
            continue
        if field_name == "place":
            layout.places.append(index)
            continue
        if field_name == "rank":
            # "клас." follows every lift, the total and the points; only the
            # one after the total is the placing in the class.
            if index and _HEADER_ALIASES.get(normalized[index - 1]) == "total":
                layout.total_rank = index
            continue
        if field_name not in layout.mapping.values():
            layout.mapping[index] = field_name
    return layout


def _norm_header(value):
    text = (value or "").lower().replace("№", "no")
    return re.sub(r"[^a-z0-9а-я]", "", text)


def _metadata(rows):
    found = {}
    labels_of_interest = {"date", "meetname", "meettown", "formula", "federation", "meetcountry"}
    for index, row in enumerate(rows):
        labels = [_norm_header(cell) for cell in row]
        for key, label in (
            ("date", "date"),
            ("title", "meetname"),
            ("city", "meettown"),
            ("formula", "formula"),
        ):
            if label not in labels:
                continue
            position = labels.index(label)
            right = row[position + 1] if position + 1 < len(row) else ""
            below = ""
            if index + 1 < len(rows) and position < len(rows[index + 1]):
                below = rows[index + 1][position]
            if right and _norm_header(right) not in labels_of_interest:
                found[key] = right
            elif below:
                found[key] = below
    return found


# A club's points line sits in the results table with a rank and a name but no
# lifts. Only a lifter who did not start carries a code instead of a result.
_NO_LIFT_PLACES = {"NS", "DQ", "DD", "G", "DNS", "DSQ"}


def _is_result_row(item):
    if (item.place or "").strip().upper() in _NO_LIFT_PLACES:
        return True
    if any(v is not None for v in (item.best_squat, item.best_bench, item.best_deadlift, item.total)):
        return True
    return any(value is not None for value in item.attempts.values())


def _cell(row, index):
    return row[index] if index < len(row) else ""


def _with_cell(row, index, value):
    row = [*row, *[""] * (index + 1 - len(row))]
    row[index] = value
    return row


def _index_of(mapping, field_name):
    return next(index for index, name in mapping.items() if name == field_name)


_TOTAL_STATUSES = {"DSQ", "DQ", "DNS", "NS", "DD"}


def _total_status(value):
    text = (value or "").strip().upper()
    return text if text in _TOTAL_STATUSES else ""


def _mapped(row, mapping, field_name, default=""):
    for index, name in mapping.items():
        if name == field_name and index < len(row):
            return row[index]
    return default


# Goodlift repeats "1 Att. 2 Att. 3 Att." once per contested lift. The number
# of attempt columns is the only reliable signal for which lifts are in the file.
_ATTEMPT_BLOCKS = {
    3: [("bench", 3)],
    4: [("bench", 4)],
    9: [("squat", 3), ("bench", 3), ("deadlift", 3)],
    12: [("squat", 4), ("bench", 4), ("deadlift", 4)],
}


# Goodlift sheets and the federation's own tables mark no failure: every attempt
# is a plain weight, and only the lift's result says which of them counted. An
# attempt above the result cannot have been good, and where several equal it
# only the last one was — a good lift may not be repeated, a failed one may.
# Attempts below the result stay as they are: nothing in the sheet tells them
# apart from a lighter opener.
def _mark_failed_attempts(item, lift, best):
    numbers = [n for n in (1, 2, 3) if item.attempts.get(f"{lift}{n}") is not None]
    if not numbers or any(item.attempts[f"{lift}{n}"] <= 0 for n in numbers):
        return
    if best is None:
        for number in numbers:
            item.attempts[f"{lift}{number}"] = -item.attempts[f"{lift}{number}"]
        return
    good = max((n for n in numbers if item.attempts[f"{lift}{n}"] == best), default=None)
    for number in numbers:
        if number != good and item.attempts[f"{lift}{number}"] >= best:
            item.attempts[f"{lift}{number}"] = -item.attempts[f"{lift}{number}"]


def _row_from_mapping(row, mapping, layout, kind):
    row_equipment = _equipment_in_text(_mapped(row, mapping, "equipment")) or ""
    item = ParsedRow(
        place=_clean_place(_mapped(row, mapping, "place")),
        raw_name=_full_name(row, mapping),
        sex=_sex_label(_mapped(row, mapping, "sex")) or "",
        country=_mapped(row, mapping, "country"),

        equipment=row_equipment,
        equipment_source="row" if row_equipment else "",
        event=_event_code(_mapped(row, mapping, "event")),
        weight_class=normalize_weight_class(_mapped(row, mapping, "weight_class")),
        bodyweight=_decimal(_mapped(row, mapping, "bodyweight")),
        age=_decimal(_mapped(row, mapping, "age")),
        club=_mapped(row, mapping, "club") or _extra_club(row, mapping),
        nation_raw=_mapped(row, mapping, "nation"),
        lot=_mapped(row, mapping, "lot"),
        points=_decimal(_mapped(row, mapping, "points")),
    )
    for index in layout.divisions:
        _apply_division(item, _cell(row, index))
    _split_masters_suffix(item)
    if kind == "opl":
        for name in (
            "squat1",
            "squat2",
            "squat3",
            "squat4",
            "bench1",
            "bench2",
            "bench3",
            "bench4",
            "deadlift1",
            "deadlift2",
            "deadlift3",
            "deadlift4",
        ):
            item.attempts[name] = _attempt(row, mapping, name)
        stated = set(mapping.values())
        for lift in ("squat", "bench", "deadlift"):
            best = _positive(_mapped(row, mapping, f"best_{lift}"))
            if f"best_{lift}" in stated:
                _mark_failed_attempts(item, lift, best)
            setattr(item, f"best_{lift}", best or _best_of(item, lift))
        item.total = _positive(_mapped(row, mapping, "total"))
    else:
        blocks = _ATTEMPT_BLOCKS.get(len(layout.attempts))
        if blocks is None:
            item.errors.append(
                f"Неразпознат Goodlift лист: {len(layout.attempts)} колони с опити. "
                "Очакват се 3 или 4 за лег и 9 или 12 за трибой."
            )
            return item
        raw_attempts = [_cell(row, index) for index in layout.attempts]
        position = 0
        for lift, count in blocks:
            for number in range(1, count + 1):
                value = _signed_kg(raw_attempts[position])
                if value is not None:
                    item.attempts[f"{lift}{number}"] = value
                position += 1
        final = _positive(_cell(row, layout.results[-1])) if layout.results else None
        if len(blocks) == 1:
            item.event = Event.B
            if layout.results:
                _mark_failed_attempts(item, "bench", final)
                item.best_bench = final
            else:
                item.best_bench = _best_of(item, "bench")
        else:
            item.event = Event.SBD
            item.best_squat = _best_of(item, "squat")
            item.best_bench = _best_of(item, "bench")
            item.best_deadlift = _best_of(item, "deadlift")
            item.total = final
        if any("X" == value.strip().upper() for value in raw_attempts):
            item.warnings.append("Има неуспешен опит без записано тегло.")
    if item.event == Event.SBD and item.total is None:
        if item.best_squat and item.best_bench and item.best_deadlift:
            item.total = item.best_squat + item.best_bench + item.best_deadlift
    return item


# A Bulgarian scoresheet marks the lift with √ or × in the labelled column and
# puts the weight in the unlabelled one beside it. The marks are specific enough
# that a plain "X", which elsewhere means a failed attempt with no weight
# recorded, is left alone.
_GOOD_MARK = {"√", "✓"}
_BAD_MARK = {"×", "✗"}


def _attempt(row, mapping, field_name):
    index = next((i for i, name in mapping.items() if name == field_name), None)
    if index is None:
        return None
    mark = _cell(row, index).strip()
    if mark in _GOOD_MARK or mark in _BAD_MARK:
        weight = _signed_kg(_cell(row, index + 1))
        if weight is None:
            return None
        return -abs(weight) if mark in _BAD_MARK else abs(weight)
    return _signed_kg(_cell(row, index))


def _full_name(row, mapping):
    """Some protocols keep the given name and the surname in two columns."""
    given = _mapped(row, mapping, "name").strip()
    surname = _mapped(row, mapping, "surname").strip()
    return f"{given} {surname}".strip() if surname else given


def _extra_club(row, mapping):
    if not mapping:
        return ""
    last = max(mapping)
    extras = [row[index] for index in range(last + 1, len(row)) if row[index]]
    if len(extras) == 1:
        return extras[0]
    return ""


def _best_of(item, lift):
    values = []
    for number in range(1, 4):
        value = item.attempts.get(f"{lift}{number}")
        if value is not None and value > 0:
            values.append(value)
    return max(values) if values else None


def _single_label(row):
    filled = [cell for cell in row if cell]
    if len(filled) == 1:
        return filled[0]
    return ""


# Goodlift ranks a lifter who failed every attempt with a dash and prints
# "disq." for the points, so the dash is a placing, not an empty cell.
_DASHES = {"\u2014", "\u2013", "-"}


def _is_place(value):
    text = (value or "").strip().upper()
    if text in {"NS", "DQ", "DD", "G", "DNS", "DSQ"} or text in _DASHES:
        return True
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return False
    return number >= 0 and number == int(number)


def _clean_place(value):
    text = (value or "").strip().upper()
    if text in _DASHES:
        return "DQ"
    if text in {"NS", "DQ", "DD", "G", "DNS", "DSQ"}:
        return {"DNS": "NS", "DSQ": "DQ"}.get(text, text)
    try:
        return str(int(float(text.replace(",", "."))))
    except ValueError:
        return text


def _sex_label(value):
    text = (value or "").strip().lower()
    if text in {"m", "мъж", "мъже", "men", "male"}:
        return Sex.M
    if text in {"f", "ж", "жена", "жени", "women", "female"}:
        return Sex.F
    return ""


# A sheet name may qualify the sex ("мъже без екип"); a section label inside the
# sheet may not, because there a stray word would capture the rows after it.
def _sex_in_text(value):
    text = (value or "").lower()
    if re.search(r"\b(мъже|мъж|men|male)\b", text):
        return Sex.M
    if re.search(r"\b(жени|жена|women|female)\b", text):
        return Sex.F
    return ""


def _division_label(value):
    text = re.sub(r"[^a-zа-я0-9]+", "", (value or "").strip().lower())
    if not text:
        return ""
    table = {
        "t1": AgeGroup.SUBJUNIOR,
        "t2": AgeGroup.SUBJUNIOR,
        "t3": AgeGroup.SUBJUNIOR,
        "sj": AgeGroup.SUBJUNIOR,
        "sjr": AgeGroup.SUBJUNIOR,
        "sjnr": AgeGroup.SUBJUNIOR,
        "subjunior": AgeGroup.SUBJUNIOR,
        "subjuniors": AgeGroup.SUBJUNIOR,
        "до18": AgeGroup.SUBJUNIOR,
        "18": AgeGroup.SUBJUNIOR,
        "юноши": AgeGroup.SUBJUNIOR,
        "юношиидевойки": AgeGroup.SUBJUNIOR,
        "jr": AgeGroup.JUNIOR,
        "junior": AgeGroup.JUNIOR,
        "juniors": AgeGroup.JUNIOR,
        "до23": AgeGroup.JUNIOR,
        "23": AgeGroup.JUNIOR,
        "младежи": AgeGroup.JUNIOR,
        "младежидо23": AgeGroup.JUNIOR,
        "девойкидо23": AgeGroup.JUNIOR,
        "o": AgeGroup.OPEN,
        "open": AgeGroup.OPEN,
        "opens": AgeGroup.OPEN,
        "открита": AgeGroup.OPEN,
        "seniors": AgeGroup.OPEN,
        "senior": AgeGroup.OPEN,
        "sr": AgeGroup.OPEN,
        "елит": AgeGroup.OPEN,
        "m1": AgeGroup.M1,
        "masters1": AgeGroup.M1,
        "ветерани1": AgeGroup.M1,
        "m2": AgeGroup.M2,
        "masters2": AgeGroup.M2,
        "ветерани2": AgeGroup.M2,
        "m3": AgeGroup.M3,
        "masters3": AgeGroup.M3,
        "ветерани3": AgeGroup.M3,
        "m4": AgeGroup.M4,
        "masters4": AgeGroup.M4,
        "ветерани4": AgeGroup.M4,
    }
    if text in table:
        return table[text]
    # Protocols glue the sex, and sometimes the equipment, onto the division:
    # "F-Jr", "MR-O", "F-C-Open". The division is the last part; the sex and the
    # equipment have columns of their own. The whole string is tried first, so
    # "Sub-Junior" is not mistaken for "Junior".
    if len(text) > 1 and text[0] in "fmw" and text[1:] in table:
        return table[text[1:]]
    code = (value or "").strip()
    # Only for something shaped like a code: a heading such as "Best Lifters of
    # Subjuniors" must stay unrecognised so it still starts a block to skip.
    if " " not in code and len(code) <= 12:
        tail = re.sub(r"[^a-zа-я0-9]+", "", re.split(r"[-/]", code)[-1].lower())
        if tail and tail != text and tail in table:
            return table[tail]
    return ""


_BG_MASTERS = {"1": AgeGroup.M1, "2": AgeGroup.M2, "3": AgeGroup.M3, "4": AgeGroup.M4}


# Bulgarian protocols spell the division out: "Жени до 18г.", "Мъже", "Ветерани
# Мъже". An unnumbered "ветерани" leaves the band open rather than guessing M1.
def _bg_division(value):
    text = (value or "").strip().lower()
    sex = _sex_in_text(text)
    if not sex:
        return "", ""
    if re.search(r"до\s*18", text):
        return sex, AgeGroup.SUBJUNIOR
    if re.search(r"до\s*23", text):
        return sex, AgeGroup.JUNIOR
    match = re.search(r"ветеран\w*\s*([1-4])", text)
    if match:
        return sex, _BG_MASTERS[match.group(1)]
    if "ветеран" in text or "мастер" in text:
        return sex, ""
    return sex, AgeGroup.OPEN


# OpenPowerlifting-style division codes such as "M-CL-PL" carry the sex, the
# equipment and the discipline in one cell, alongside a plain age division.
_CODE_EQUIPMENT = {"CL": Equipment.CLASSIC, "R": Equipment.CLASSIC, "RAW": Equipment.CLASSIC,
                   "EQ": Equipment.EQUIPPED, "SP": Equipment.EQUIPPED}
_CODE_EVENT = {"PL": Event.SBD, "BP": Event.B, "DL": Event.D, "PP": Event.PP}


# When the division column says only "Ветерани", the band is appended to the
# name instead. Left in place it would also register the lifter under it.
def _split_masters_suffix(item):
    match = re.search(r"\s+[\u041cM]([1-4])\s*$", item.raw_name)
    if not match:
        return
    item.raw_name = item.raw_name[: match.start()].strip()
    item.age_group = item.age_group or _BG_MASTERS[match.group(1)]


def _apply_division(item, value):
    text = (value or "").strip().upper()
    match = re.fullmatch(r"([FMW])-([A-Z]{1,3})-([A-Z]{2})", text)
    if match:
        sex, equipment, event = match.groups()
        item.sex = item.sex or (Sex.F if sex in "FW" else Sex.M)
        if not item.equipment and equipment in _CODE_EQUIPMENT:
            item.equipment = _CODE_EQUIPMENT[equipment]
            item.equipment_source = "row"
        item.event = item.event or _CODE_EVENT.get(event, "")
        return
    sex, age_group = _bg_division(value)
    if sex:
        item.sex = item.sex or sex
        item.age_group = item.age_group or age_group
        return
    item.age_group = item.age_group or _division_label(value)


def _looks_like_class_label(value):
    text = (value or "").strip().lower()
    return bool(re.fullmatch(r"-?\s*\d+(?:[.,]\d+)?\s*\+?\s*(?:kg|кг)?", text))


def normalize_weight_class(value):
    text = (value or "").strip().lower().replace("кг", "").replace("kg", "").replace(" ", "")
    text = text.replace(",", ".")
    if not text:
        return ""
    plus = text.endswith("+") or text.startswith("+")
    text = text.strip("+-")
    if text.startswith("-"):
        text = text[1:]
    try:
        number = Decimal(text)
    except InvalidOperation:
        return ""
    whole = str(int(number)) if number == int(number) else format(number.normalize(), "f")
    return f"{whole}+" if plus else whole


def _equipment_in_text(value):
    text = (value or "").lower()
    # "с и без екип" is a combined round: the file alone cannot say which lifter
    # wore a suit, so it stays unset and the operator has to choose.
    if re.search(r"с\s+и\s+без\s+екип", text) or ("с екип" in text and "без екип" in text):
        return ""
    if any(word in text for word in ("без екип", "classic", "raw", "класик", "класическ")):
        return Equipment.CLASSIC
    if any(word in text for word in ("екип", "equipped", "single-ply", "single ply")):
        return Equipment.EQUIPPED
    return ""


def _event_in_text(value):
    text = (value or "").lower()
    if "трибой" in text or "powerlifting" in text:
        return Event.SBD
    if "лег" in text or "bench" in text:
        return Event.B
    return ""


def _mentions_deadlift(value):
    text = (value or "").lower()
    return "мъртва тяга" in text or "deadlift" in text


# Which lifts a meet contested is a property of the sheet's columns, not of one
# row: a lifter who fails all three squats still competed in a full-power meet.
def _event_from_columns(mapping):
    def has(lift):
        names = {f"{lift}{n}" for n in range(1, 5)} | {f"best_{lift}"}
        return bool(names & set(mapping.values()))

    squat, bench, deadlift = has("squat"), has("bench"), has("deadlift")
    if squat and bench and deadlift:
        return Event.SBD
    if bench and deadlift:
        return Event.PP
    if deadlift:
        return Event.D
    return Event.B


def _event_code(value):
    text = (value or "").strip().upper()
    if text in {Event.SBD, Event.B}:
        return text
    return ""


def _date_in_text(value):
    # A meet over several days is written "19-21.09.2025" or "30.05-01.06.2025";
    # the date that belongs to it is the first day, not the last.
    match = (
        re.search(r"(?<!\d)(\d{1,2})[.](\d{1,2})\s*[-–]\s*\d{1,2}[.]\d{1,2}[.](\d{4})", value or "")
        or re.search(r"(?<!\d)(\d{1,2})\s*[-–]\s*\d{1,2}[.](\d{1,2})[.](\d{4})", value or "")
        or re.search(r"(\d{1,2})[.](\d{1,2})[.](\d{4})", value or "")
    )
    if match:
        day, month, year = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", value or "")
    if match:
        year, month, day = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _parse_date(value):
    text = (value or "").strip()
    if not text:
        return None
    text = text[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _decimal(value):
    text = (value or "").strip().replace(",", ".").replace(" ", "")
    if not text or text.upper() == "X":
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _signed_kg(value):
    text = (value or "").strip()
    if not text or text.upper() == "X":
        return None
    return _decimal(text)


def _positive(value):
    number = _decimal(value)
    if number is None or number <= 0:
        return None
    return number
