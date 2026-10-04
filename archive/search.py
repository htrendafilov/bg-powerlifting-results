"""Case-insensitive athlete names.

SQLite's LIKE folds only ASCII, so a query for "крум" misses "Крум".
Each connection gets unicode_lower(), and the search compares casefolded names.
"""

from django.db.backends.signals import connection_created
from django.db.models import CharField, Func, Q


def _unicode_lower(value):
    if not isinstance(value, str):
        return value
    return value.casefold()


def install_unicode_lower(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    connection.connection.create_function(
        "unicode_lower", 1, _unicode_lower, deterministic=True
    )


def connect():
    connection_created.connect(install_unicode_lower, dispatch_uid="archive.unicode_lower")


class UnicodeLower(Func):
    function = "unicode_lower"
    output_field = CharField()


def match_athlete_name(athletes, query):
    folded = query.casefold()
    return athletes.alias(
        name_bg_fold=UnicodeLower("name_bg"),
        name_lat_fold=UnicodeLower("name_lat"),
    ).filter(Q(name_bg_fold__contains=folded) | Q(name_lat_fold__contains=folded))
