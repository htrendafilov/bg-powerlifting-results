"""Merging two records of the same lifter into one.

The sources spell the same person differently — "Robert Michailov" and
"Robert Mihailov", "Vladimir Christov" and "Vladimir Hristov" — and a Bulgarian
protocol writes three names where an international one writes two. Exact
matching cannot join those, so they are joined by hand.
"""

import difflib

from django.db import transaction

from archive.models import AthleteAlias, Athlete
from archive.services.names import name_tokens
from archive.services.records import recalculate_records


_MERGE_NOTE = "Слети: "


@transaction.atomic
def merge_athletes(target, others, *, recalculate=True):
    """Move every start, record and photo onto target, then delete the rest."""
    absorbed = []
    for other in others:
        if other.pk == target.pk:
            continue
        other.results.update(athlete=target)
        other.records.update(athlete=target)
        other.photos.update(athlete=target)
        _fill_gaps(target, other)
        other.aliases.update(athlete=target)
        if other.name_key and other.name_key != target.name_key:
            AthleteAlias.objects.update_or_create(
                name_key=other.name_key, sex=other.sex, defaults={"athlete": target}
            )
        absorbed.append(other.display_name or other.name_lat or str(other.pk))
        other.delete()
    # The same spelling can come back from a later import, so a name already
    # recorded must not be appended a second time.
    already = {
        name.strip()
        for line in (target.notes or "").splitlines()
        if line.startswith(_MERGE_NOTE)
        for name in line[len(_MERGE_NOTE):].split(", ")
    }
    fresh = [name for name in absorbed if name not in already]
    if fresh:
        note = _MERGE_NOTE + ", ".join(fresh)
        target.notes = f"{target.notes}\n{note}".strip() if target.notes else note
    target.save()
    if absorbed and recalculate:
        # Records point at results that have just changed hands.
        recalculate_records()
    return absorbed


def _fill_gaps(target, other):
    # A name read from a Bulgarian protocol beats one converted from Latin.
    if target.name_bg_auto and other.name_bg and not other.name_bg_auto:
        target.name_bg = other.name_bg
        target.name_bg_auto = False
    for field in ("name_bg", "name_lat", "birth_year"):
        if not getattr(target, field) and getattr(other, field):
            setattr(target, field, getattr(other, field))
    target.adult_confirmed = target.adult_confirmed or other.adult_confirmed
    if other.notes and other.notes not in (target.notes or ""):
        target.notes = f"{target.notes}\n{other.notes}".strip() if target.notes else other.notes


def duplicate_candidates(threshold=0.86, limit=200):
    """Pairs that look like one person written two ways, closest first."""
    athletes = list(Athlete.objects.all())
    buckets = {}
    for athlete in athletes:
        tokens = name_tokens(athlete.name_lat) or name_tokens(athlete.name_bg)
        if not tokens:
            continue
        # Two spellings of a name almost always agree on some first letter, so
        # only compare within the same sex and starting letters.
        for token in tokens:
            buckets.setdefault((athlete.sex, token[0]), set()).add(athlete.pk)

    by_pk = {a.pk: a for a in athletes}
    seen = set()
    pairs = []
    for members in buckets.values():
        members = sorted(members)
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                if (left, right) in seen:
                    continue
                seen.add((left, right))
                one, two = by_pk[left], by_pk[right]
                # Namesakes already told apart by birth year are not a duplicate.
                if one.birth_year and two.birth_year and one.birth_year != two.birth_year:
                    continue
                score = _similarity(one, two)
                if score >= threshold:
                    pairs.append((score, one, two))
    pairs.sort(key=lambda item: item[0], reverse=True)
    return pairs[:limit]


def _similarity(one, two):
    def key(athlete):
        return " ".join(sorted(name_tokens(athlete.name_lat) or name_tokens(athlete.name_bg)))

    left, right = key(one), key(two)
    if not left or not right:
        return 0.0
    score = difflib.SequenceMatcher(None, left, right).ratio()
    # "Ivan Petrov Ivanov" against "Ivan Ivanov": one name is a subset of the
    # other, which the plain ratio scores low but is the common Bulgarian case.
    left_set, right_set = set(left.split()), set(right.split())
    if left_set < right_set or right_set < left_set:
        score = max(score, 0.9)
    return score
