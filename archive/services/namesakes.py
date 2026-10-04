"""Telling apart different lifters who go by the same name.

Two people with one name get two profiles, and nothing else on the page says
which is which, so each is labelled with the years they competed and the club
they last lifted for.
"""

from collections import Counter

from archive.models import Athlete, Result
from archive.services.visibility import visible_athletes, visible_results


def shared_names():
    athletes = visible_athletes(Athlete.objects.only("name_bg", "name_lat"))
    counts = Counter(athlete.display_name for athlete in athletes)
    return {name for name, count in counts.items() if count > 1}


def namesakes_of(athlete):
    if athlete.name_bg:
        same = Athlete.objects.filter(name_bg=athlete.name_bg)
    else:
        same = Athlete.objects.filter(name_bg="", name_lat=athlete.name_lat)
    return list(visible_athletes(same.exclude(pk=athlete.pk)))


def career_hints(athletes):
    spans = {}
    rows = (
        visible_results(Result.objects.filter(athlete__in=athletes))
        .order_by("competition__start_date")
        .values_list("athlete_id", "competition__start_date", "club")
    )
    for pk, day, club in rows:
        first, _, last_club = spans.get(pk, (day.year, None, ""))
        spans[pk] = (first, day.year, club.strip() or last_club)
    hints = {}
    for pk, (first, last, club) in spans.items():
        years = str(first) if first == last else f"{first}–{last}"
        hints[pk] = f"{years} · {club}" if club else years
    return hints
