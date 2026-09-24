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

# The IPF replaced its classes on 1 January 2011, then split the women's 72 kg
# into 69 and 76 on 1 January 2021. The men's classes were untouched by the
# second change, so only the women's list has three eras.
NEW_RULES_FROM = date(2011, 1, 1)
SPLIT_RULES_FROM = date(2021, 1, 1)

LIMITS = {
    ("M", "new"): ["53", "59", "66", "74", "83", "93", "105", "120"],
    ("F", "new"): ["43", "47", "52", "57", "63", "69", "76", "84"],
    ("M", "mid"): ["53", "59", "66", "74", "83", "93", "105", "120"],
    ("F", "mid"): ["47", "52", "57", "63", "72", "84"],
    ("M", "old"): ["52", "56", "60", "67.5", "75", "82.5", "90", "100", "110", "125"],
    ("F", "old"): ["44", "48", "52", "56", "60", "67.5", "75", "82.5", "90"],
}
# The lightest class is contested by the youngest age groups only.
YOUTH_ONLY = {("M", "new"): "53", ("F", "new"): "43", ("M", "mid"): "53", ("F", "mid"): "",
              ("M", "old"): "52", ("F", "old"): "44"}
YOUTH_GROUPS = {"subjunior", "junior"}


def weight_class_for(sex, bodyweight, day, age_group=""):
    if bodyweight is None or sex not in ("M", "F"):
        return ""
    if day >= SPLIT_RULES_FROM:
        era = "new"
    elif day >= NEW_RULES_FROM:
        era = "mid"
    else:
        era = "old"
    limits = list(LIMITS[(sex, era)])
    youth = YOUTH_ONLY[(sex, era)]
    if age_group not in YOUTH_GROUPS and limits[0] == youth:
        limits = limits[1:]
    weight = Decimal(str(bodyweight))
    for limit in limits:
        if weight <= Decimal(limit):
            return limit
    return f"{limits[-1]}+"


# The bounds of each era, so a stored class can be judged against the rules that
# were in force when the meet was held rather than against today's list.
ERA_BOUNDS = {
    "old": (None, NEW_RULES_FROM),
    "mid": (NEW_RULES_FROM, SPLIT_RULES_FROM),
    "new": (SPLIT_RULES_FROM, None),
}
MODERN_ERAS = ("mid", "new")


def classes_of(sex, era):
    limits = LIMITS[(sex, era)]
    return set(limits) | {f"{limits[-1]}+"}


def era_for(day):
    if day >= SPLIT_RULES_FROM:
        return "new"
    return "mid" if day >= NEW_RULES_FROM else "old"


def class_fits(sex, weight_class, bodyweight, day):
    """Whether a protocol's stated class can be true of this weigh-in.

    Two ways it cannot: the class was not contested that year, or the lifter
    weighed more than it allows. A lifter is never lighter than the scale said.
    """
    if sex not in ("M", "F") or not weight_class:
        return True
    if weight_class not in classes_of(sex, era_for(day)):
        return False
    if weight_class.endswith("+") or bodyweight is None:
        return True
    return Decimal(str(bodyweight)) <= Decimal(weight_class)


def sex_for_class(weight_class, day):
    """The sex a class belongs to, where only one sex contests it.

    Since 2011 the men's and the women's lists share no class, so a protocol
    that mixes both without saying which is which still says it through the
    class. Before 2011 they overlapped and the class tells nothing.
    """
    era = era_for(day)
    if era not in MODERN_ERAS or not weight_class:
        return ""
    owners = [sex for sex in ("M", "F") if weight_class in classes_of(sex, era)]
    return owners[0] if len(owners) == 1 else ""
