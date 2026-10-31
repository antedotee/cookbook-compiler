"""Phase 3: semantic analysis. Checks meaning against the kitchen rules and builds the symbol table.

Unlike phases 1 and 2, this phase keeps going after a problem so it can report every one.
"""

import difflib
from dataclasses import dataclass

from .kitchen import (
    DISHES, DURATION_UNIT, INGREDIENTS, MAX_MINUTES, MIN_MINUTES, UNITS, WHOLE_UNITS, Stage,
)
from .model import AddStep, Diagnostic, Recipe, ServeStep, Span, TimedStep, fmt_number

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
        fail("dish", f"unknown dish '{dish}'{_suggest(dish, DISHES)}, choose one of {', '.join(DISHES)}", recipe.dish.span)
    order = _OrderChecker(dish, stages, fail) if stages else None
    dish_ingredients = set().union(*(stage.adds for stage in stages)) if stages else set(INGREDIENTS)

    amounts: dict[str, list[tuple[float, str]]] = {}
    first_line: dict[str, int] = {}
    served_line = None

    for step in recipe.steps:
        if served_line is not None:
            fail("serve", f"nothing can come after SERVE on line {served_line}", step.span)
            continue

        if isinstance(step, AddStep):
            name = step.ingredient.text
            if name not in INGREDIENTS:
                fail("ingredient", f"unknown ingredient '{name}'{_suggest(name, INGREDIENTS)}", step.ingredient.span)
                continue
            if name not in dish_ingredients:
                fail("ingredient", f"{name} does not belong in {dish}", step.ingredient.span)
                continue
            if _check_amount(step, fail):
                amounts.setdefault(name, []).append((step.amount.value, step.unit.text))
                first_line.setdefault(name, step.span.line)
            if order:
                order.add(step)

        elif isinstance(step, TimedStep):
            _check_duration(step, fail)
            if order:
                order.cook(step)

        elif isinstance(step, ServeStep):
            served_line = step.span.line
            if order:
                order.serve(step)

    if served_line is None:
        end = recipe.steps[-1].span if recipe.steps else recipe.span
        fail("serve", "the recipe must end with SERVE;", end)

    symbols = [{"name": dish, "kind": "dish", "unit": "", "total": "", "first_line": recipe.dish.span.line}]
    symbols += [_symbol(name, used, first_line[name]) for name, used in amounts.items()]
    return SemanticResult(symbols, _checklist(problems), [diagnostic for _, diagnostic in problems])


def _check_amount(step: AddStep, fail) -> bool:
    """Check the unit and amount of an ADD. Returns True when the unit is valid for the ingredient."""
    name, unit, amount = step.ingredient.text, step.unit.text, step.amount.value
    allowed = INGREDIENTS[name]
    if unit not in UNITS:
        fail("unit", f"unknown unit '{unit}'{_suggest(unit, UNITS)}, use one of {', '.join(UNITS)}", step.unit.span)
        return False
    if unit not in allowed:
        fail("unit", f"{name} is measured in {' or '.join(allowed)}, not {unit}", step.unit.span)
        return False
    if amount <= 0:
        fail("range", f"the amount of {name} must be greater than 0", step.amount.span)
        return False
    if unit in WHOLE_UNITS and amount != int(amount):
        fail("range", f"{name} must be a whole number of {unit}, not {step.amount.text}", step.amount.span)
        return False
    return True


def _check_duration(step: TimedStep, fail) -> None:
    if step.unit.text != DURATION_UNIT:
        fail("unit", f"{step.verb} time must be in {DURATION_UNIT}, not {step.unit.text}", step.unit.span)
    if not MIN_MINUTES <= step.duration.value <= MAX_MINUTES:
        fail("range", f"{step.verb} time must be between {MIN_MINUTES} and {MAX_MINUTES} minutes, not {step.duration.text}",
             step.duration.span)


class _OrderChecker:
    """A state machine over the dish's stages.

    State is (stage index, whether that stage's cook step has run). An ADD after cooking opens the next
    stage. The same cook verb repeated right after itself continues the current stage.
    """

    def __init__(self, dish: str, stages: tuple[Stage, ...], fail):
        self.dish, self.stages, self.fail = dish, stages, fail
        self.pos, self.cooked, self.added = 0, False, set()

    def next_stage(self) -> None:
        self.pos, self.cooked, self.added = self.pos + 1, False, set()

    def cook_name(self, index: int) -> str:
        verb = self.stages[index].cook
        same = [i for i, stage in enumerate(self.stages) if stage.cook == verb]
        if len(same) == 1:
            return verb
        return f"the {('first', 'second', 'third')[same.index(index)]} {verb}"

    def add(self, step: AddStep) -> None:
        name = step.ingredient.text
        if self.cooked:
            self.next_stage()
        if self.pos >= len(self.stages):
            self.fail("order", f"{name} is added after the last cooking step, only SERVE can come now", step.span)
            return
        if name in self.stages[self.pos].adds:
            self.added.add(name)
            return
        home = next(i for i, stage in enumerate(self.stages) if name in stage.adds)
        if home < self.pos:
            self.fail("order", f"{name} comes too late, {self.dish} adds it before {self.cook_name(home)}", step.span)
        else:
            self.fail("order", f"{name} comes too early, {self.dish} adds it after {self.cook_name(home - 1)}", step.span)

    def cook(self, step: TimedStep) -> None:
        if self.cooked and step.verb == self.stages[self.pos].cook:
            return
        if self.cooked:
            self.next_stage()
        if self.pos >= len(self.stages):
            self.fail("order", f"{self.dish} needs no more cooking after {self.cook_name(len(self.stages) - 1)}, SERVE it", step.span)
            return
        stage = self.stages[self.pos]
        if step.verb != stage.cook:
            later = any(s.cook == step.verb for s in self.stages[self.pos + 1:])
            reason = f"{self.dish} must {self.cook_name(self.pos)} first" if later else f"the next step for {self.dish} is {stage.cook}"
            self.fail("order", f"{step.verb} on line {step.span.line} is out of order, {reason}", step.span)
            return
        missing = sorted(stage.adds - self.added)
        if missing:
            self.fail("order", f"{step.verb} on line {step.span.line} needs {', '.join(missing)} added first", step.span)
        self.cooked = True

    def serve(self, step: ServeStep) -> None:
        first_left = self.pos + 1 if self.cooked else self.pos
        left = [self.cook_name(i) for i in range(first_left, len(self.stages))]
        if left:
            self.fail("order", f"{self.dish} is served before {', '.join(left)}", step.span)


def _symbol(name: str, used: list[tuple[float, str]], first_line: int) -> dict:
    units = {unit for _, unit in used}
    if len(units) == 1:
        unit = units.pop()
        total = sum(amount for amount, _ in used)
    else:
        unit = UNITS[used[0][1]][0]
        total = sum(amount * UNITS[u][1] for amount, u in used)
    return {"name": name, "kind": "ingredient", "unit": unit, "total": fmt_number(total), "first_line": first_line}


def _checklist(problems: list[tuple[str, Diagnostic]]) -> list[dict]:
    checks = []
    for rule, description in RULES.items():
        found = [d for r, d in problems if r == rule]
        message = description if not found else found[0].message + (f" (and {len(found) - 1} more)" if len(found) > 1 else "")
        lines = sorted({d.span.line for d in found})
        checks.append({"rule": description, "ok": not found, "message": message, "lines": lines})
    return checks


def _suggest(word: str, choices) -> str:
    match = difflib.get_close_matches(word, list(choices), n=1)
    return f" (did you mean {match[0]}?)" if match else ""
