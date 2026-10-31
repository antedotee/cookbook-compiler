"""Everything the compiler knows about cooking. No other module hard-codes a dish, ingredient, or unit."""

from dataclasses import dataclass

# Allowed amount units for each ingredient.
INGREDIENTS: dict[str, tuple[str, ...]] = {
    "FLOUR": ("CUP", "SPOON"),
    "SUGAR": ("CUP", "SPOON"),
    "SALT": ("CUP", "SPOON"),
    "PASTA": ("CUP", "SPOON"),
    "TEA_LEAVES": ("CUP", "SPOON"),
    "MILK": ("CUP", "SPOON"),
    "WATER": ("CUP", "SPOON"),
    "EGG": ("PIECE",),
}

# Amount unit -> (base unit, how many base units it equals).
UNITS: dict[str, tuple[str, int]] = {
    "CUP": ("SPOON", 16),
    "SPOON": ("SPOON", 1),
    "PIECE": ("PIECE", 1),
}

WHOLE_UNITS = {"PIECE"}
MAX_AMOUNT = 1000

COOK_VERBS = ("MIX", "BOIL", "BAKE")
DURATION_UNIT = "MINUTES"
MIN_MINUTES = 1
MAX_MINUTES = 180


@dataclass(frozen=True)
class Stage:
    """Add every ingredient in `adds` (any order), then run `cook` one or more times in a row."""

    adds: frozenset[str]
    cook: str


def _stage(adds: str, cook: str) -> Stage:
    return Stage(frozenset(adds.split()), cook)


# Each dish is an ordered list of stages, followed by SERVE.
DISHES: dict[str, tuple[Stage, ...]] = {
    "CAKE": (_stage("FLOUR SUGAR EGG MILK", "MIX"), _stage("", "BAKE")),
    "PASTA": (_stage("WATER", "BOIL"), _stage("PASTA SALT", "BOIL")),
    "TEA": (_stage("WATER", "BOIL"), _stage("TEA_LEAVES MILK", "BOIL")),
}


def vocab() -> dict:
    """The vocabulary as JSON, used to fill the Blockly dropdowns."""
    return {
        "dishes": list(DISHES),
        "ingredients": list(INGREDIENTS),
        "units": list(UNITS),
        "cook_verbs": list(COOK_VERBS),
        "duration_unit": DURATION_UNIT,
        "max_amount": MAX_AMOUNT,
        "min_minutes": MIN_MINUTES,
        "max_minutes": MAX_MINUTES,
    }
