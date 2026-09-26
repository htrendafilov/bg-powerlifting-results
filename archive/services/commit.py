import os
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.files.base import File
from django.core.files.storage import default_storage
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
from archive.services.names import (
    athlete_name_key, is_cyrillic, normalize_name, reverse_transliterate, transliterate,
)
from archive.services.records import recalculate_records
from archive.services.weight_classes import class_fits, sex_for_class, weight_class_for

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


class ReplaceScopeError(Exception):
    pass


REPLACE_FILE, REPLACE_ALL, KEEP = "file", "all", "keep"


def matching_source(competition, filename):
    # A copy given its own title is recognised by the name it was stored under.
    if not filename:
        return None
    stored = default_storage.get_valid_name(filename)
    for item in competition.files.filter(kind=FileKind.EXCEL).exclude(file=""):
        if item.title == filename or os.path.basename(item.file.name) == stored:
            return item
    return None


def _content_changed(source, stored_file):
    stored_file.seek(0)
    incoming = stored_file.read()
    stored_file.seek(0)
    try:
        with source.file.open("rb") as handle:
            return handle.read() != incoming
    except FileNotFoundError:
        return True


def rows_to_replace(competition, source, mode, *, keeps_file):
    """The results a re-import takes the place of.

    Only the rows of the same file are replaced, so a meet published as several
    files keeps the others. A row loaded before sources were tracked belongs to
    no file; it is replaced only where it cannot have come from another one.
    """
    results = competition.results.all()
    if mode == KEEP:
        return results.none()
    if mode == REPLACE_ALL:
        return results
    known = source is not None and source.pk is not None
    own = results.filter(source=source) if known else results.none()
    elsewhere = results.filter(source__isnull=False)
    stored = competition.files.filter(kind=FileKind.EXCEL).exclude(file="")
    if known:
        elsewhere = elsewhere.exclude(source=source)
        stored = stored.exclude(pk=source.pk)
    if not keeps_file and elsewhere.exists():
        raise ReplaceScopeError(
            f"Турнирът има {elsewhere.count()} реда от запазени файлове. Закачи файла, "
            "за да се знае кои редове подменя, или замени целия турнир изрично."
        )
    unlinked = results.filter(source__isnull=True)
    if unlinked.exists() and (elsewhere.exists() or stored.exists()):
        raise ReplaceScopeError(
            f"Не е ясно от кой файл са {unlinked.count()} по-стари реда на турнира. "
            "Замени целия турнир изрично или само добави."
        )
    return own | unlinked


def apply_import(competition, parsed, *, default_sex, default_equipment, default_event, default_age_group="", reclass=False, replace, stored_file=None, filename="", title=""):
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

    keeps_file = stored_file is not None and bool(filename)
    source = matching_source(competition, filename) if keeps_file else None
    doomed = rows_to_replace(competition, source, replace, keeps_file=keeps_file)
    with transaction.atomic():
        doomed.delete()
        if keeps_file and source is None:
            source = CompetitionFile.objects.create(
                competition=competition,
                kind=FileKind.EXCEL,
                title=title or filename,
                file=File(stored_file, name=filename),
            )
        elif keeps_file and _content_changed(source, stored_file):
            # A corrected protocol under the same name: the copy kept here must
            # be the one the rows now come from.
            source.file.delete(save=False)
            source.file.save(filename, File(stored_file, name=filename))
        created_athletes = 0
        created = 0
        entries = {}
        for item in ready:
            athlete, was_created, certain = find_athlete(
                item.raw_name, item.sex, _hints(item, competition.start_date)
            )
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
                source=source,
            )
            for field_name in ATTEMPT_FIELDS:
                setattr(result, field_name, item.attempts.get(field_name))
            notes = [NAMESAKE_NOTE] if not certain else []
            contradicted = _contradicted_lifts(item)
            if contradicted:
                notes += [CONTRADICTION_NOTE.format(lift=_LIFT_NAMES[lift]) for lift in contradicted]
                result.counts_for_records = False
            result.review_note = " · ".join(notes)[:300]
            result.save()
            entries.setdefault((athlete.pk, result.event, result.equipment, result.age_group), []).append(result)
            created += 1
        # Two rows of one division on one profile are two people with one name.
        for rows in entries.values():
            if len(rows) > 1:
                Result.objects.filter(pk__in=[r.pk for r in rows], review_note="").update(review_note=SHARED_NOTE)
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
        if not item.sex and meet_date:
            item.sex = sex_for_class(item.weight_class, meet_date)
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
        # A lift failed three times leaves no total and so no placing, whatever
        # number the protocol printed beside it (Варна 2025).
        if _bombed_out(item) and (item.place or "").strip().isdigit():
            item.place = "DQ"
        for lift in _contradicted_lifts(item):
            item.warnings.append(CONTRADICTION_NOTE.format(lift=_LIFT_NAMES[lift]))
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
        match = _match_state(item, meet_date) if item.raw_name and item.sex else None
        if match == "ambiguous":
            item.warnings.append(NAMESAKE_NOTE)
        if problems:
            blocked.append({"row": index, "name": item.raw_name, "problems": problems})
            continue
        item.match = match
        ready.append(item)
    return ready, blocked


def _match_state(item, meet_date):
    key = athlete_name_key(item.raw_name if is_cyrillic(item.raw_name) else "", item.raw_name)
    namesakes = list(Athlete.objects.filter(sex=item.sex, name_key=key).order_by("pk"))
    if len(namesakes) > 1:
        _, certain = _pick_namesake(namesakes, _hints(item, meet_date))
        return "existing" if certain else "ambiguous"
    if namesakes:
        return "existing"
    return "new"


NAMESAKE_NOTE = "Има няколко състезатели с това име — провери дали профилът е верният."
CONTRADICTION_NOTE = (
    "Най-добрият {lift} в протокола е отбелязан като неуспешен опит — не се брои за рекорд, "
    "докато организаторът не каже кое е вярно."
)
_EVENT_LIFTS = {Event.SBD: ("squat", "bench", "deadlift"), Event.B: ("bench",),
                Event.D: ("deadlift",), Event.PP: ("bench", "deadlift")}
_LIFT_NAMES = {"squat": "клек", "bench": "лег", "deadlift": "тяга"}


def _attempts(item, lift):
    return [v for v in (item.attempts.get(f"{lift}{n}") for n in (1, 2, 3)) if v is not None]


def _bombed_out(item):
    for lift in _EVENT_LIFTS.get(item.event, ()):
        attempts = _attempts(item, lift)
        if attempts and all(value <= 0 for value in attempts):
            return True
    return False


def _contradicted_lifts(item):
    """Lifts whose stated best is not the heaviest attempt marked good.

    Only where the attempts carry their own signs; a negative best is
    OpenPowerlifting's way of saying the lift was failed, not a contradiction.
    """
    found = []
    for lift in _EVENT_LIFTS.get(item.event, ()):
        attempts = _attempts(item, lift)
        best = getattr(item, f"best_{lift}")
        if not attempts or best is None or best <= 0 or all(value > 0 for value in attempts):
            continue
        if max((value for value in attempts if value > 0), default=None) != best:
            found.append(lift)
    return found
SHARED_NOTE = "Два реда от протокола в една дивизия сочат към един профил — вероятно двама души."

# Calendar-year ages of the IPF divisions, the way a federation checks them.
DIVISION_AGES = {AgeGroup.SUBJUNIOR: (14, 18), AgeGroup.JUNIOR: (19, 23), AgeGroup.M1: (40, 49),
                 AgeGroup.M2: (50, 59), AgeGroup.M3: (60, 69), AgeGroup.M4: (70, 150)}


@dataclass
class Hints:
    """What a row says about who the lifter is, beyond the name."""

    meet_date: date | None = None
    ages: tuple | None = None
    club: str = ""
    birth_year: int | None = None


def _hints(item, meet_date):
    return Hints(meet_date=meet_date, ages=DIVISION_AGES.get(item.age_group), club=item.club,
                 birth_year=item.birth_year)


def athlete_for(raw_name, sex, hints=None):
    athlete, created, _ = find_athlete(raw_name, sex, hints)
    return athlete, created


def find_athlete(raw_name, sex, hints=None):
    """The athlete a row belongs to, whether it was created, and whether the
    choice is certain — it is not when namesakes cannot be told apart."""
    hints = hints or Hints()
    raw_name = normalize_name(raw_name)
    key = athlete_name_key(raw_name if is_cyrillic(raw_name) else "", raw_name)
    namesakes = list(Athlete.objects.filter(sex=sex, name_key=key).order_by("pk"))
    if len(namesakes) == 1:
        return namesakes[0], False, True
    if namesakes:
        athlete, certain = _pick_namesake(namesakes, hints)
        return athlete, False, certain
    # A spelling that was merged away must not come back as a new athlete.
    alias = AthleteAlias.objects.filter(sex=sex, name_key=key).select_related("athlete").first()
    if alias:
        return alias.athlete, False, True
    if is_cyrillic(raw_name):
        athlete = Athlete(name_bg=raw_name, name_lat=transliterate(raw_name), sex=sex)
    else:
        athlete = Athlete(name_lat=raw_name, sex=sex)
    athlete.birth_year = hints.birth_year
    athlete.save()
    return athlete, True, True


def _pick_namesake(namesakes, hints):
    if hints.birth_year:
        born = [a for a in namesakes if a.birth_year == hints.birth_year]
        if len(born) == 1:
            return born[0], True
    possible = namesakes
    if hints.ages and hints.meet_date:
        low, high = hints.ages
        possible = [
            a for a in namesakes
            if a.birth_year is None or low <= hints.meet_date.year - a.birth_year <= high
        ] or namesakes
        if len(possible) == 1:
            return possible[0], True
    club = _club_key(hints.club)
    if club:
        same_club = [a for a in possible if club in _clubs_of(a)]
        if len(same_club) == 1:
            return same_club[0], True
    return possible[0], False


def _club_key(text):
    # "NSA", "Нса" and "НСА;" are one club; protocols switch alphabets.
    return re.sub(r"[^0-9а-я]", "", reverse_transliterate(text or "").lower())


def _clubs_of(athlete):
    return {_club_key(club) for club in athlete.results.values_list("club", flat=True)} - {""}


def decimal_or_blank(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value)
