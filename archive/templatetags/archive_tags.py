from decimal import Decimal

from django import template

register = template.Library()


def format_kg(value):
    if isinstance(value, Decimal):
        text = format(value, "f")
    else:
        text = str(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@register.inclusion_tag("archive/attempt.html")
def attempt(value):
    if value is None:
        return {"text": "–", "kind": "empty"}
    if value < 0:
        return {"text": format_kg(abs(value)), "kind": "miss"}
    return {"text": format_kg(value), "kind": "good"}


@register.inclusion_tag("archive/lift_cells.html")
def lift_cells(result, lift):
    attempts = [getattr(result, f"{lift}{number}") for number in (1, 2, 3)]
    best = getattr(result, f"best_{lift}")
    # A protocol that kept only the best lift has no attempts; its best spans
    # the three columns instead of reading as an opener.
    only_best = best is not None and all(value is None for value in attempts)
    return {"lift": lift, "attempts": attempts, "best": best, "only_best": only_best}


@register.filter
def kg(value):
    if value is None:
        return "–"
    return format_kg(value)
