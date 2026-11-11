"""Phase 3: semantic analysis. Checks meaning against the kitchen rules and builds the symbol table.

Unlike phases 1 and 2, this phase keeps going after a problem so it can report every one.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from .kitchen import DISHES, DURATION_UNIT, INGREDIENTS, MAX_AMOUNT, MAX_DECIMALS, MAX_MINUTES, MIN_MINUTES, UNITS, WHOLE_UNITS
from .model import AddStep, Diagnostic, Recipe, Span, TimedStep, fmt_number
from .order import OrderStep, check_order

RULES = {
    "dish": "The dish is one the kitchen knows",
    "ingredient": "Every ingredient is known and belongs in the dish",
    "unit": "Every unit suits its ingredient or step",
    "range": "Amounts and cooking times are in range",
    "order": "Steps follow the dish's order",
    "serve": "The recipe ends with SERVE",
}


@dataclass
class SemanticResult:
    symbols: list[dict]
    checks: list[dict]
    errors: list[Diagnostic]


def analyze(recipe: Recipe) -> SemanticResult:
    problems: list[tuple[str, Diagnostic]] = []

    def fail(rule: str, message: str, span: Span) -> None:
        problems.append((rule, Diagnostic(message, span)))

    dish = recipe.dish.text
    stages = DISHES.get(dish)
    if stages is None:
        fail("dish", f"unknown dish '{_short(dish)}'{_suggest(dish, DISHES)}, choose one of {', '.join(DISHES)}",
             recipe.dish.span)
    dish_ingredients = set().union(*(stage.adds for stage in stages)) if stages else set(INGREDIENTS)

    amounts: dict[str, list[tuple[float, str]]] = {}
    first_line: dict[str, int] = {}
    order_steps: list[OrderStep] = []

    for step in recipe.steps:
        if isinstance(step, AddStep):
            name = step.ingredient.text
            if name not in INGREDIENTS:
                fail("ingredient", f"unknown ingredient '{_short(name)}'{_suggest(name, INGREDIENTS)}", step.ingredient.span)
            elif name not in dish_ingredients:
                fail("ingredient", f"{name} does not belong in {dish}", step.ingredient.span)
            elif _check_amount(step, fail):
                amounts.setdefault(name, []).append((step.amount.value, step.unit.text))
                first_line.setdefault(name, step.span.line)
            symbol = ("ADD", name) if name in dish_ingredients else ("ADD", None)
            order_steps.append(OrderStep(symbol, step.span))
        elif isinstance(step, TimedStep):
            _check_duration(step, fail)
            order_steps.append(OrderStep(("COOK", step.verb), step.span))
        else:
            order_steps.append(OrderStep(("SERVE", ""), step.span))

    end = recipe.steps[-1].span if recipe.steps else recipe.span
    if not recipe.steps:
        fail("serve", f"the recipe has no steps, a {dish} needs its ingredients, its cooking, and SERVE;" if stages
             else "the recipe has no steps", recipe.span)
    elif stages:
        problems += check_order(dish, stages, order_steps, end)
    else:
        _check_serve_only(order_steps, end, fail)

    unchecked = {"order", "ingredient"} if stages is None else set()
    symbols = [{"name": dish, "kind": "dish", "unit": "", "total": "", "first_line": recipe.dish.span.line}]
    symbols += [_symbol(name, used, first_line[name]) for name, used in amounts.items()]
    problems.sort(key=lambda p: (p[1].span.line, p[1].span.col))
    return SemanticResult(symbols, _checklist(problems, unchecked), [diagnostic for _, diagnostic in problems])


def _check_serve_only(steps: list[OrderStep], end: Span, fail) -> None:
    """Without a known dish only the SERVE rules can be checked."""
    serves = [i for i, step in enumerate(steps) if step.symbol[0] == "SERVE"]
    if not serves:
        fail("serve", "the recipe must end with SERVE;", end)
    elif serves[0] < len(steps) - 1:
        after = steps[serves[0] + 1]
        extra = len(steps) - serves[0] - 1
        more = f" ({extra} steps follow it)" if extra > 1 else ""
        fail("serve", f"nothing can come after SERVE on line {steps[serves[0]].span.line}{more}", after.span)


def _check_amount(step: AddStep, fail) -> bool:
    """Check the unit and amount of an ADD. Returns True when the unit is valid for the ingredient."""
    name, unit, amount = step.ingredient.text, step.unit.text, step.amount.value
    allowed = INGREDIENTS[name]
    if unit not in UNITS:
        fail("unit", f"unknown unit '{_short(unit)}'{_suggest(unit, UNITS)}, use one of {', '.join(UNITS)}", step.unit.span)
        return False
    if unit not in allowed:
        fail("unit", f"{name} is measured in {' or '.join(allowed)}, not {unit}", step.unit.span)
        return False
    if not 0 < amount <= MAX_AMOUNT:
        fail("range", f"the amount of {name} must be greater than 0 and at most {MAX_AMOUNT}", step.amount.span)
        return False
    if _decimals(step.amount.text) > MAX_DECIMALS:
        fail("range", f"amounts can have at most {MAX_DECIMALS} decimal places, not {step.amount.text}", step.amount.span)
        return False
    if unit in WHOLE_UNITS and amount != int(amount):
        fail("range", f"{name} must be a whole number of {unit}, not {step.amount.text}", step.amount.span)
        return False
    return True


def _check_duration(step: TimedStep, fail) -> None:
    if step.unit.text != DURATION_UNIT:
        fail("unit", f"{step.verb} time must be in {DURATION_UNIT}, not {step.unit.text}", step.unit.span)
    if _decimals(step.duration.text) > MAX_DECIMALS:
        fail("range", f"times can have at most {MAX_DECIMALS} decimal places, not {step.duration.text}", step.duration.span)
    elif not MIN_MINUTES <= step.duration.value <= MAX_MINUTES:
        fail("range", f"{step.verb} time must be between {MIN_MINUTES} and {MAX_MINUTES} minutes, not {step.duration.text}",
             step.duration.span)


def _symbol(name: str, used: list[tuple[float, str]], first_line: int) -> dict:
    """Total in the unit the recipe used, or in the base unit when it mixed units."""
    units = {unit for _, unit in used}
    if len(units) == 1:
        unit = units.pop()
        total = sum(amount for amount, _ in used)
    else:
        unit = UNITS[used[0][1]][0]
        total = sum(amount * UNITS[u][1] for amount, u in used)
    return {"name": name, "kind": "ingredient", "unit": unit, "total": fmt_number(total), "first_line": first_line}


def _checklist(problems: list[tuple[str, Diagnostic]], unchecked: set[str]) -> list[dict]:
    """One entry per rule. ok is True, False, or None when the rule could not be checked."""
    checks = []
    for rule, description in RULES.items():
        found = [d for r, d in problems if r == rule]
        if found:
            ok, message = False, found[0].message + (f" (and {len(found) - 1} more)" if len(found) > 1 else "")
        elif rule in unchecked:
            ok, message = None, f"{description}: not checked, because the dish is unknown"
        else:
            ok, message = True, description
        checks.append({"rule": description, "ok": ok, "message": message, "lines": sorted({d.span.line for d in found})})
    return checks


def _decimals(text: str) -> int:
    return len(text.split(".")[1].rstrip("0")) if "." in text else 0


def _short(name: str) -> str:
    return name if len(name) <= 30 else name[:27] + "..."


def _suggest(word: str, choices) -> str:
    match = difflib.get_close_matches(word, list(choices), n=1)
    return f" (did you mean {match[0]}?)" if match else ""
