"""What the site shows, given the setting for the old weight classes.

A result in a pre-2011 class is hidden; a competition disappears once every one
of its results is hidden, but one that has no results yet stays, because it is
still a meet the archive knows about. An athlete disappears the same way.
"""

from django.db.models import Q

from archive.models import CURRENT_WEIGHT_CLASSES, Result, SiteSettings


def showing_old_classes():
    return SiteSettings.load().show_old_weight_classes


def current_classes_q(prefix=""):
    field = f"{prefix}weight_class"
    sex = f"{prefix}sex"
    query = Q(**{f"{field}": ""})
    for value, classes in CURRENT_WEIGHT_CLASSES.items():
        query |= Q(**{sex: value, f"{field}__in": classes})
    return query


def visible_results(queryset=None):
    queryset = Result.objects.all() if queryset is None else queryset
    if showing_old_classes():
        return queryset
    return queryset.filter(current_classes_q())


def visible_records(queryset):
    if showing_old_classes():
        return queryset
    return queryset.filter(current_classes_q())


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
