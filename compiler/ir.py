"""Phase 4: intermediate code. One simple instruction per step, still in the units the cook wrote."""

from __future__ import annotations

from .model import AddStep, IRInstr, Recipe, TimedStep, fmt_number


def generate(recipe: Recipe) -> list[IRInstr]:
    code = []
    for step in recipe.steps:
        lines = (step.span.line,)
        if isinstance(step, AddStep):
            code.append(IRInstr("add", step.amount.value, step.unit.text, step.ingredient.text, lines))
        elif isinstance(step, TimedStep):
            code.append(IRInstr(step.verb.lower(), step.duration.value, "MIN", lines=lines))
        else:
            code.append(IRInstr("serve", lines=lines))
    return code


def render(code: list[IRInstr]) -> list[dict]:
    rows = []
    for number, instr in enumerate(code, start=1):
        if instr.op == "add":
            body = f"add {instr.ingredient}, {fmt_number(instr.amount)} {instr.unit}"
        elif instr.op == "serve":
            body = "serve"
        else:
            body = f"{instr.op} {fmt_number(instr.amount)} {instr.unit}"
        rows.append({"text": f"t{number} = {body}", "lines": list(instr.lines)})
    return rows
