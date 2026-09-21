from decimal import Decimal

from django.core.files.base import File
from django.db import transaction

from archive.models import Athlete, CompetitionFile, Event, FileKind, Result
from archive.services.names import athlete_name_key, is_cyrillic, transliterate
from archive.services.records import recalculate_records

ATTEMPT_FIELDS = [
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
]


def apply_import(competition, parsed, *, default_sex, default_equipment, default_event, replace, stored_file=None, filename=""):
    ready, blocked = prepare_rows(parsed, default_sex=default_sex, default_equipment=default_equipment, default_event=default_event)
    if blocked:
        return {"created": 0, "athletes": 0, "blocked": blocked}

    with transaction.atomic():
        if replace:
            competition.results.all().delete()
        created_athletes = 0
        created = 0
        for item in ready:
            athlete, was_created = _athlete_for(item)
            created_athletes += int(was_created)
            result = Result(
                competition=competition,
                athlete=athlete,
                raw_name=item.raw_name,
                country=item.country or "България",
                sex=item.sex,
                age_group=item.age_group,
                equipment=item.equipment,
                event=item.event,
                weight_class=item.weight_class,
                bodyweight=item.bodyweight,
                place=item.place,
                club=item.club,
                lot=item.lot,
                best_squat=item.best_squat,
                best_bench=item.best_bench,
                best_deadlift=item.best_deadlift,
                total=item.total,
                points=item.points,
                points_formula=item.points_formula or parsed.formula,
            )
            for field_name in ATTEMPT_FIELDS:
                setattr(result, field_name, item.attempts.get(field_name))
            result.save()
            created += 1
        if stored_file is not None and filename:
            CompetitionFile.objects.create(
                competition=competition,
                kind=FileKind.EXCEL,
                title=filename,
                file=File(stored_file, name=filename),
            )
        recalculate_records()
    return {"created": created, "athletes": created_athletes, "blocked": []}


def prepare_rows(parsed, *, default_sex, default_equipment, default_event):
    ready = []
    blocked = []
    for index, item in enumerate(parsed.rows, start=1):
        item.sex = item.sex or default_sex
        item.equipment = item.equipment or default_equipment
        if not item.event or item.event == "auto":
            item.event = "" if default_event == "auto" else default_event
        if default_event and default_event != "auto":
            item.event = default_event
        problems = list(item.errors)
        if not item.sex:
            problems.append("Няма пол. Избери пол в импорта.")
        if not item.age_group:
            problems.append("Няма възрастова група.")
        if not item.equipment:
            problems.append("Няма екипировка.")
        if item.event not in {Event.SBD, Event.B}:
            problems.append("Няма дисциплина.")
        if not item.weight_class and item.place not in {"NS", "DQ", "DD", "G"}:
            problems.append("Няма категория.")
        match = _match_state(item) if item.raw_name and item.sex else None
        if match == "ambiguous":
            problems.append("Има повече от един състезател с това име.")
        if problems:
            blocked.append({"row": index, "name": item.raw_name, "problems": problems})
            continue
        item.match = match
        ready.append(item)
    return ready, blocked


def _match_state(item):
    key = athlete_name_key(item.raw_name if is_cyrillic(item.raw_name) else "", item.raw_name)
    count = Athlete.objects.filter(sex=item.sex, name_key=key).count()
    if count > 1:
        return "ambiguous"
    if count == 1:
        return "existing"
    return "new"


def _athlete_for(item):
    key = athlete_name_key(item.raw_name if is_cyrillic(item.raw_name) else "", item.raw_name)
    existing = list(Athlete.objects.filter(sex=item.sex, name_key=key)[:1])
    if existing:
        return existing[0], False
    if is_cyrillic(item.raw_name):
        athlete = Athlete(name_bg=item.raw_name, name_lat=transliterate(item.raw_name), sex=item.sex)
    else:
        athlete = Athlete(name_lat=item.raw_name, sex=item.sex)
    athlete.save()
    return athlete, True


def decimal_or_blank(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value)
