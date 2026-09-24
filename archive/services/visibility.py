"""What the site shows, given the setting for the old weight classes.

A result in a pre-2011 class is hidden; a competition disappears once every one
of its results is hidden, but one that has no results yet stays, because it is
still a meet the archive knows about. An athlete disappears the same way.
"""

from django.db.models import Q

from archive.models import Result, SiteSettings
from archive.services.weight_classes import ERA_BOUNDS, MODERN_ERAS, classes_of


def showing_old_classes():
    return SiteSettings.load().show_old_weight_classes


def current_classes_q(prefix="", date_field=""):
    """Judge the class against the rules of the meet's own era.

    The women's 72 kg ran until the end of 2020, so a 2018 result in it is not
    an old-rules result, while the same class in 2023 is a mistake. Anything
    before 2011 is hidden outright, which is what the setting is for.
    """
    field = f"{prefix}weight_class"
    sex = f"{prefix}sex"
    date_field = date_field or f"{prefix}competition__start_date"
    query = Q(**{f"{field}": ""})
    for era in MODERN_ERAS:
        start, end = ERA_BOUNDS[era]
        for value in ("M", "F"):
            clause = Q(**{sex: value, f"{field}__in": classes_of(value, era)})
            clause &= Q(**{f"{date_field}__gte": start})
            if end is not None:
                clause &= Q(**{f"{date_field}__lt": end})
            query |= clause
    return query


def visible_results(queryset=None):
    queryset = Result.objects.all() if queryset is None else queryset
    if showing_old_classes():
        return queryset
    return queryset.filter(current_classes_q())


def visible_records(queryset):
    if showing_old_classes():
        return queryset
    return queryset.filter(current_classes_q(date_field="valid_from"))


def visible_competitions(queryset):
    return _hide_emptied(queryset, "competition_id")


def visible_athletes(queryset):
    return _hide_emptied(queryset, "athlete_id")


def _hide_emptied(queryset, column):
    """Drop rows whose every result is hidden, keeping those that have none."""
    if showing_old_classes():
        return queryset
    with_any = set(Result.objects.values_list(column, flat=True))
    with_visible = set(visible_results().values_list(column, flat=True))
    return queryset.exclude(pk__in=with_any - with_visible)
