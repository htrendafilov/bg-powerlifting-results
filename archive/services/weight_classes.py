"""Working out which class a lifter was in from the weigh-in bodyweight.

Some protocols — the Sheffield invitational among them — record the bodyweight
but no class, because the meet is scored on points rather than by class. A
record is kept per class, so without one the result can never reach the tables
even though it was set at a sanctioned meet.

The class is whatever the bodyweight put the lifter in, which is exactly how a
federation assigns it, so this is a reading of the data rather than a guess.
"""

from datetime import date
from decimal import Decimal

# The IPF replaced its classes on 1 January 2011.
NEW_RULES_FROM = date(2011, 1, 1)

LIMITS = {
    ("M", "new"): ["53", "59", "66", "74", "83", "93", "105", "120"],
    ("F", "new"): ["43", "47", "52", "57", "63", "69", "76", "84"],
    ("M", "old"): ["52", "56", "60", "67.5", "75", "82.5", "90", "100", "110", "125"],
    ("F", "old"): ["44", "48", "52", "56", "60", "67.5", "75", "82.5", "90"],
}
# The lightest class is contested by the youngest age groups only.
YOUTH_ONLY = {("M", "new"): "53", ("F", "new"): "43", ("M", "old"): "52", ("F", "old"): "44"}
YOUTH_GROUPS = {"subjunior", "junior"}


def weight_class_for(sex, bodyweight, day, age_group=""):
    if bodyweight is None or sex not in ("M", "F"):
        return ""
    era = "new" if day >= NEW_RULES_FROM else "old"
    limits = list(LIMITS[(sex, era)])
    youth = YOUTH_ONLY[(sex, era)]
    if age_group not in YOUTH_GROUPS and limits[0] == youth:
        limits = limits[1:]
    weight = Decimal(str(bodyweight))
    for limit in limits:
        if weight <= Decimal(limit):
            return limit
    return f"{limits[-1]}+"
