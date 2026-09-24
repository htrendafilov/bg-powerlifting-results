from decimal import Decimal

from django.core.files.base import File
from django.db import transaction

from archive.models import (
    BG_COUNTRIES,
    AgeGroup,
    Athlete,
    AthleteAlias,
    CompetitionFile,
    Event,
    FileKind,
    MeetLevel,
    NON_SCORING_PLACES,
    Result,
)
from archive.services.names import athlete_name_key, is_cyrillic, normalize_name, transliterate
from archive.services.records import recalculate_records
from archive.services.weight_classes import class_fits, weight_class_for

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


def apply_import(competition, parsed, *, default_sex, default_equipment, default_event, default_age_group="", reclass=False, replace, stored_file=None, filename=""):
    ready, blocked = prepare_rows(
        parsed,
        default_sex=default_sex,
        default_equipment=default_equipment,
        default_event=default_event,
        default_age_group=default_age_group,
        reclass=reclass,
        meet_level=competition.level,
        meet_date=competition.start_date,
    )
    if blocked:
        return {"created": 0, "athletes": 0, "blocked": blocked}
    home_country = "България" if competition.level == MeetLevel.NATIONAL else ""

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
                country=_country_for(item.country, home_country),
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
        # Re-importing the same protocol must not attach a second copy of it,
        # while a meet published as several files keeps all of them.
        if stored_file is not None and filename and not competition.files.filter(
            kind=FileKind.EXCEL, title=filename
        ).exists():
            CompetitionFile.objects.create(
                competition=competition,
                kind=FileKind.EXCEL,
                title=filename,
                file=File(stored_file, name=filename),
            )
        recalculate_records()
    return {"created": created, "athletes": created_athletes, "blocked": []}


# IPF age divisions, used when a protocol gives the age in years but no group.
_AGE_BANDS = [(18, AgeGroup.SUBJUNIOR), (23, AgeGroup.JUNIOR), (39, AgeGroup.OPEN),
              (49, AgeGroup.M1), (59, AgeGroup.M2), (69, AgeGroup.M3)]


def _age_group_for(age):
    years = int(age)
    if years < 13 or years > 100:
        return ""
    for limit, group in _AGE_BANDS:
        if years <= limit:
            return group
    return AgeGroup.M4


def _country_for(value, home_country):
    text = (value or "").strip()
    if not text:
        return home_country
    return "България" if text.lower() in BG_COUNTRIES else text


def prepare_rows(parsed, *, default_sex, default_equipment, default_event,
                 default_age_group="", reclass=False, meet_level=MeetLevel.NATIONAL,
                 meet_date=None):
    ready = []
    blocked = []
    for index, item in enumerate(parsed.rows, start=1):
        item.sex = item.sex or default_sex
        # A per-row Equipment column beats the operator, who in turn beats a
        # guess made from the meet title.
        if item.equipment_source not in {"row", "sheet"} and default_equipment != "auto":
            item.equipment = default_equipment
        if default_event != "auto":
            item.event = default_event
        elif item.event == "auto":
            item.event = ""
        if not item.age_group and item.age:
            item.age_group = _age_group_for(item.age)
        item.age_group = item.age_group or default_age_group
        # A lifter who does not score was never in a class; reading one off the
        # scale would file her where she did not compete.
        scoring = (item.place or "").strip().upper() not in NON_SCORING_PLACES
        if reclass and item.bodyweight and scoring:
            item.weight_class = ""
        # A class the year did not contest, or one lighter than the weigh-in,
        # cannot be what the lifter competed in; the bodyweight decides instead.
        if item.weight_class and meet_date and scoring and not class_fits(
            item.sex, item.weight_class, item.bodyweight, meet_date
        ):
            item.weight_class = ""
        if not item.weight_class and item.bodyweight and meet_date and scoring:
            item.weight_class = weight_class_for(
                item.sex, item.bodyweight, meet_date, item.age_group
            )
        problems = list(item.errors)
        if not item.sex:
            problems.append("Няма пол. Избери пол в импорта.")
        if not item.age_group:
            problems.append("Няма възрастова група.")
        if not item.equipment:
            problems.append("Няма екипировка. Изборът „с и без екип“ трябва да се направи в импорта.")
        if item.event not in set(Event.values):
            problems.append("Няма дисциплина.")
        if not item.weight_class and item.place not in {"NS", "DQ", "DD", "G"}:
            problems.append("Няма категория.")
        if meet_level == MeetLevel.INTERNATIONAL and not item.country:
            problems.append("Няма държава. На международен турнир тя не се подразбира.")
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
    return athlete_for(item.raw_name, item.sex)


def athlete_for(raw_name, sex):
    raw_name = normalize_name(raw_name)
    key = athlete_name_key(raw_name if is_cyrillic(raw_name) else "", raw_name)
    existing = list(Athlete.objects.filter(sex=sex, name_key=key)[:1])
    if existing:
        return existing[0], False
    # A spelling that was merged away must not come back as a new athlete.
    alias = AthleteAlias.objects.filter(sex=sex, name_key=key).select_related("athlete").first()
    if alias:
        return alias.athlete, False
    if is_cyrillic(raw_name):
        athlete = Athlete(name_bg=raw_name, name_lat=transliterate(raw_name), sex=sex)
    else:
        athlete = Athlete(name_lat=raw_name, sex=sex)
    athlete.save()
    return athlete, True


def decimal_or_blank(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value)
