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


@register.filter
def kg(value):
    if value is None:
        return "–"
    return format_kg(value)
