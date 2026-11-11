"""Checks that a recipe's steps follow its dish's order, and explains each mistake once.

Each dish's order is a small finite automaton built from its stages in kitchen.py. Instead of stopping at
the first step the automaton rejects, the checker finds the fewest edits that turn the recipe into one the
automaton accepts, then reports one error per edit. The edits are: remove a step, insert a missing step,
replace a step, or swap two neighbouring steps. Compilers call this minimum-distance error recovery. It
means one mistake gives one error, and later correct steps are never blamed for an earlier mistake.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Optional, Tuple
from dataclasses import dataclass

from .kitchen import Stage
from .model import Diagnostic, Span

# A symbol is what a step means to the automaton: ("ADD", ingredient), ("COOK", verb), or ("SERVE", "").
# An ingredient already reported as misspelled or not in the dish is ("ADD", None). It stands in for
# whichever step fits there, or can be dropped at no cost, so one mistake is never reported twice.
Symbol = Tuple[str, Optional[str]]

# Edit costs as (mistakes, tie-break). The tie-break picks the most natural explanation among
# explanations with the same number of mistakes.
FREE = (0, 0)
COST = {"insert_add": (1, 1), "swap": (1, 2), "remove": (1, 3), "insert_cook": (1, 4), "replace": (1, 5),
        "insert_serve": (1, 6), "remove_unclear": (0, 1)}


@dataclass(frozen=True)
class OrderStep:
    symbol: Symbol
    span: Span


@dataclass(frozen=True)
class Edit:
    op: str  # match, remove, insert, replace, swap
    index: int  # position in the steps
    state: tuple  # automaton state before the edit
    symbol: Symbol | None = None  # the symbol inserted or replaced with
    after: tuple | None = None  # automaton state after the edit


def check_order(dish: str, stages: tuple[Stage, ...], steps: list[OrderStep], end: Span) -> list[tuple[str, Diagnostic]]:
    """Returns (rule, diagnostic) pairs. The rule is "order", or "serve" for SERVE problems."""
    automaton = _Automaton(stages)
    edits = _cheapest_edits(automaton, steps)
    return _Explainer(dish, stages, steps, end).explain(edits)


class _Automaton:
    """States: ("add", stage, frozenset of ingredients added so far), ("cooked", stage), ("served",)."""

    def __init__(self, stages: tuple[Stage, ...]):
        self.stages = stages
        self.start = ("add", 0, frozenset())
        self.accept = ("served",)
        ingredients = sorted(set().union(*(stage.adds for stage in stages)))
        verbs = sorted({stage.cook for stage in stages})
        self.alphabet: list[Symbol] = [("ADD", name) for name in ingredients] + [("COOK", v) for v in verbs] + [("SERVE", "")]

    def move(self, state: tuple, symbol: Symbol) -> list[tuple]:
        kind, name = symbol
        if kind == "ADD" and name is None:
            return [s for candidate in self.alphabet for s in self.move(state, candidate)]
        if state[0] == "served":
            return []
        if state[0] == "cooked":
            index = state[1]
            if symbol == ("COOK", self.stages[index].cook):
                return [state]
            if symbol == ("SERVE", "") and index == len(self.stages) - 1:
                return [self.accept]
            if index + 1 < len(self.stages):
                return self.move(("add", index + 1, frozenset()), symbol)
            return []
        _, index, added = state
        stage = self.stages[index]
        if kind == "ADD" and name in stage.adds:
            return [("add", index, added | {name})]
        if symbol == ("COOK", stage.cook) and added == stage.adds:
            return [("cooked", index)]
        return []


def _cheapest_edits(automaton: _Automaton, steps: list[OrderStep]) -> list[Edit]:
    """Dijkstra over (steps read, automaton state). Finds the cheapest path to reading every step and serving."""
    start = (0, automaton.start)
    best = {start: FREE}
    back: dict = {}
    tie = itertools.count()
    queue = [(FREE, next(tie), start)]
    goal = None

    def push(node, cost, step_cost, edit):
        total = (cost[0] + step_cost[0], cost[1] + step_cost[1])
        if total < best.get(node, (float("inf"), 0)):
            best[node] = total
            back[node] = (current, edit)
            heapq.heappush(queue, (total, next(tie), node))

    while queue:
        cost, _, current = heapq.heappop(queue)
        if cost > best[current]:
            continue
        index, state = current
        if index == len(steps) and state == automaton.accept:
            goal = current
            break
        if index < len(steps):
            symbol = steps[index].symbol
            unclear = symbol == ("ADD", None)
            for after in automaton.move(state, symbol):
                push((index + 1, after), cost, FREE, Edit("match", index, state, after=after))
            push((index + 1, state), cost, COST["remove_unclear" if unclear else "remove"], Edit("remove", index, state))
            if not unclear:
                for other in automaton.alphabet:
                    if other != symbol:
                        for after in automaton.move(state, other):
                            push((index + 1, after), cost, COST["replace"], Edit("replace", index, state, other, after))
            if index + 1 < len(steps) and steps[index + 1].symbol != symbol and not unclear:
                for middle in automaton.move(state, steps[index + 1].symbol):
                    for after in automaton.move(middle, symbol):
                        push((index + 2, after), cost, COST["swap"], Edit("swap", index, state, after=after))
        for other in automaton.alphabet:
            for after in automaton.move(state, other):
                kind = {"ADD": "insert_add", "COOK": "insert_cook", "SERVE": "insert_serve"}[other[0]]
                push((index, after), cost, COST[kind], Edit("insert", index, state, other, after))

    edits = []
    node = goal
    while node != start:
        node, edit = back[node]
        edits.append(edit)
    return edits[::-1]


class _Explainer:
    """Turns edits into messages a student can act on."""

    def __init__(self, dish: str, stages: tuple[Stage, ...], steps: list[OrderStep], end: Span):
        self.dish, self.stages, self.steps, self.end = dish, stages, steps, end

    def explain(self, edits: list[Edit]) -> list[tuple[str, Diagnostic]]:
        edits = self.pair_moves(edits)
        out: list[tuple[str, Diagnostic]] = []
        served_line = None
        pending: list[Edit] = []  # consecutive inserts of the same kind at one position

        def flush():
            if pending:
                out.append(self.inserted(pending))
                pending.clear()

        for edit in edits:
            if edit.op == "insert":
                if pending and (pending[0].index != edit.index or pending[0].symbol[0] != edit.symbol[0]):
                    flush()
                pending.append(edit)
                continue
            flush()
            step = self.steps[edit.index]
            if edit.op == "match":
                if step.symbol[0] == "SERVE":
                    served_line = step.span.line
            elif edit.op == "remove" and edit.state[0] == "served":
                if not out or not out[-1][1].message.startswith("nothing can come after SERVE"):
                    following = sum(1 for e in edits if e.op == "remove" and e.state[0] == "served")
                    more = f" ({following} steps follow it)" if following > 1 else ""
                    out.append(("serve", Diagnostic(f"nothing can come after SERVE on line {served_line}{more}", step.span)))
            elif edit.op == "remove" and step.symbol != ("ADD", None):
                out.append(("order", Diagnostic(self.removed(step.symbol, edit.state), step.span)))
            elif edit.op == "replace":
                out.append(("order", Diagnostic(self.replaced(step.symbol, edit), step.span)))
            elif edit.op == "swap":
                second = self.steps[edit.index + 1]
                message = f"{_action(second.symbol)} must come before {_action(step.symbol)}, swap these two steps"
                out.append(("order", Diagnostic(message, step.span)))
        flush()
        return out

    def pair_moves(self, edits: list[Edit]) -> list[Edit]:
        """A step written in the wrong place costs a removal plus an insertion of the same step. Keep only
        the removal, whose message already says where the step belongs, so the move is one error."""
        removed = {self.steps[e.index].symbol for e in edits if e.op == "remove" and e.state[0] != "served"}
        kept, dropped = [], set()
        for edit in edits:
            if edit.op == "insert" and edit.symbol in removed and edit.symbol not in dropped and edit.symbol[0] != "SERVE":
                dropped.add(edit.symbol)
                continue
            kept.append(edit)
        return kept

    # Helpers that read the automaton state.

    def next_stage(self, state: tuple) -> int:
        """Index of the stage whose cook step comes next."""
        if state[0] == "served":
            return len(self.stages)
        return state[1] + 1 if state[0] == "cooked" else state[1]

    def cook_name(self, index: int) -> str:
        verb = self.stages[index].cook
        same = [i for i, stage in enumerate(self.stages) if stage.cook == verb]
        if len(same) == 1:
            return verb
        nth = same.index(index)
        return f"the {('first', 'second', 'third')[nth] if nth < 3 else f'{nth + 1}th'} {verb}"

    def stage_of(self, ingredient: str) -> int:
        return next(i for i, stage in enumerate(self.stages) if ingredient in stage.adds)

    def recipe(self) -> str:
        return f"the {self.dish} recipe"

    # One message per kind of edit.

    def inserted(self, group: list[Edit]) -> tuple[str, Diagnostic]:
        index = group[0].index
        span = self.steps[index].span if index < len(self.steps) else self.end
        kind = group[0].symbol[0]
        if kind == "SERVE":
            return "serve", Diagnostic("the recipe must end with SERVE;", span)
        if kind == "ADD":
            names = _join(sorted(e.symbol[1] for e in group))
            stage = group[-1].after[1]
            here = self.steps[index].symbol if index < len(self.steps) else None
            subject = here[1] if here == ("COOK", self.stages[stage].cook) else self.cook_name(stage)
            return "order", Diagnostic(f"{subject} needs {names} added first", span)
        names = _join([self.cook_name(e.after[1]) for e in group])
        verb = "is" if len(group) == 1 else "are"
        if index >= len(self.steps):
            return "order", Diagnostic(f"{self.dish} still needs {names} before SERVE", span)
        here = self.steps[index].symbol
        if here[0] == "SERVE":
            return "order", Diagnostic(f"{self.dish} is served before {names}", span)
        return "order", Diagnostic(f"{names} {verb} missing before {_action(here)}", span)

    def removed(self, symbol: Symbol, state: tuple) -> str:
        kind, name = symbol
        upcoming = self.next_stage(state)
        if kind == "SERVE":
            left = _join([self.cook_name(i) for i in range(upcoming, len(self.stages))]) or "more steps"
            return f"SERVE comes too early, {self.dish} still needs {left}"
        if kind == "ADD":
            home = self.stage_of(name)
            if home > upcoming:
                return f"{name} comes too early, {self.recipe()} adds it after {self.cook_name(home - 1)}"
            if home < upcoming:
                return f"{name} comes too late, {self.recipe()} adds it before {self.cook_name(home)}"
            return f"{name} is added more times than needed here"
        if all(stage.cook != name for stage in self.stages):
            return f"{name} is not a step of {self.dish}"
        if upcoming >= len(self.stages):
            return f"{self.dish} needs no more cooking after {self.cook_name(len(self.stages) - 1)}, SERVE it"
        stage = self.stages[upcoming]
        if name == stage.cook:
            missing = _join(sorted(stage.adds - (state[2] if state[0] == "add" else frozenset())))
            return f"{name} comes too early, {self.recipe()} adds {missing} first"
        if any(s.cook == name for s in self.stages[upcoming + 1:]):
            return f"{name} comes too early, {self.dish} must {self.cook_name(upcoming)} first"
        return f"{name} comes too late, the next cooking step is {self.cook_name(upcoming)}"

    def replaced(self, symbol: Symbol, edit: Edit) -> str:
        kind, name = symbol
        want_kind, want = edit.symbol
        if want_kind == "SERVE":
            return f"{self.dish} is ready here, write SERVE instead of {_action(symbol)}"
        wanted = want if want_kind == "ADD" else self.cook_name(edit.after[1])
        if kind == "SERVE":
            needed = f"{want} added" if want_kind == "ADD" else wanted
            return f"SERVE comes too early, {self.dish} needs {needed} here"
        if kind == "COOK" and want_kind == "COOK":
            if all(stage.cook != name for stage in self.stages):
                return f"{name} is not a step of {self.dish}, the step here is {wanted}"
            return f"{name} is in the wrong place, the step here is {wanted}"
        if kind == "COOK":
            return f"{name} comes too early, {want} must be added first"
        return f"{self.recipe()} needs {wanted} here, not {name}"


def _word(symbol: Symbol) -> str:
    return symbol[1] or symbol[0]


def _action(symbol: Symbol) -> str:
    """The step as a phrase: 'adding EGG', 'MIX', 'SERVE'."""
    return f"adding {symbol[1]}" if symbol[0] == "ADD" and symbol[1] else _word(symbol)


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""
