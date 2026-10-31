"""Phase 3: semantic analysis. Checks meaning against the kitchen rules and builds the symbol table.

Unlike phases 1 and 2, this phase keeps going after a problem so it can report every one.
"""

import difflib
from dataclasses import dataclass

from .kitchen import (
    DISHES, DURATION_UNIT, INGREDIENTS, MAX_AMOUNT, MAX_MINUTES, MIN_MINUTES, UNITS, WHOLE_UNITS, Stage,
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
                if order:
                    order.unknown_add()
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
    if not 0 < amount <= MAX_AMOUNT:
        fail("range", f"the amount of {name} must be greater than 0 and at most {MAX_AMOUNT}", step.amount.span)
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

    State is the current stage index and whether its cook step has run. An ADD after cooking opens the
    next stage, and the same cook verb repeated right after itself continues the current stage.

    Each mistake is reported once. After an error the checker records what the step implies (an early
    ingredient counts toward its own stage, an early cook step marks its stage done) so later correct
    steps are not blamed for it.
    """

    def __init__(self, dish: str, stages: tuple[Stage, ...], fail):
        self.dish, self.stages, self.fail = dish, stages, fail
        self.pos, self.cooked = 0, False
        self.added: set[str] = set()
        self.accounted: set[int] = set()  # stages already reported, or cooked out of order
        self.missing_reported: set[str] = set()
        self.unclear_adds: set[int] = set()  # stages with a misspelled ingredient

    def stage_of(self, name: str) -> int:
        return next(i for i, stage in enumerate(self.stages) if name in stage.adds)

    def next_pos(self) -> int:
        return self.pos + 1 if self.cooked else self.pos

    def enter(self, index: int) -> None:
        if index != self.pos:
            self.pos, self.cooked = index, False

    def cook_name(self, index: int) -> str:
        verb = self.stages[index].cook
        same = [i for i, stage in enumerate(self.stages) if stage.cook == verb]
        if len(same) == 1:
            return verb
        nth = same.index(index)
        ordinal = ("first", "second", "third")[nth] if nth < 3 else f"{nth + 1}th"
        return f"the {ordinal} {verb}"

    def unknown_add(self) -> None:
        """An ADD of a misspelled ingredient. Don't also report that its stage is missing that ingredient."""
        self.enter(self.next_pos())
        self.unclear_adds.add(self.pos)

    def add(self, step: AddStep) -> None:
        name = step.ingredient.text
        self.enter(self.next_pos())
        self.added.add(name)
        if self.pos >= len(self.stages):
            self.fail("order", f"{name} is added after the last cooking step, only SERVE can come now", step.span)
            return
        home = self.stage_of(name)
        if home > self.pos:
            self.fail("order", f"{name} comes too early, {self.dish} adds it after {self.cook_name(home - 1)}", step.span)
        elif home < self.pos and name not in self.missing_reported:
            self.fail("order", f"{name} comes too late, {self.dish} adds it before {self.cook_name(home)}", step.span)

    def cook(self, step: TimedStep) -> None:
        verb = step.verb
        if self.cooked and self.pos < len(self.stages) and verb == self.stages[self.pos].cook:
            return
        target = self.next_pos()
        if target >= len(self.stages):
            self.fail("order", f"{self.dish} needs no more cooking after {self.cook_name(len(self.stages) - 1)}, SERVE it", step.span)
            return
        if verb == self.stages[target].cook:
            self.enter(target)
            self.check_ingredients(step, target)
            self.cooked = True
            return

        later = next((i for i in range(target + 1, len(self.stages)) if self.stages[i].cook == verb), None)
        if later is None:
            uses = any(stage.cook == verb for stage in self.stages)
            reason = "comes too late" if uses else f"is not a step of {self.dish}"
            self.fail("order", f"{verb} {reason}, the next cooking step is {self.cook_name(target)}", step.span)
            return
        self.fail("order", f"{verb} comes too early, {self.dish} must {self.cook_name(target)} first", step.span)
        self.accounted.update(range(target, later + 1))

    def check_ingredients(self, step: TimedStep, index: int) -> None:
        missing = sorted(self.stages[index].adds - self.added)
        if missing and index not in self.unclear_adds:
            self.fail("order", f"{step.verb} needs {', '.join(missing)} added first", step.span)
            self.missing_reported.update(missing)

    def serve(self, step: ServeStep) -> None:
        left = [self.cook_name(i) for i in range(self.next_pos(), len(self.stages)) if i not in self.accounted]
        if left:
            self.fail("order", f"{self.dish} is served before {', '.join(left)}", step.span)


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
