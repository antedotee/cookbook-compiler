"""Phase 6: target code. Pseudo-assembly for an imaginary kitchen machine.

    PUT <ingredient>, <amount>   amount in SPOON or PIECE
    MIX | BOIL | BAKE <seconds>
    SERVE
    HALT
"""

from __future__ import annotations

from .model import IRInstr, fmt_lines, fmt_number

COLUMN = 18


def generate(code: list[IRInstr]) -> list[dict]:
    lines = []
    for instr in code:
        if instr.op == "add":
            text = f"PUT {instr.ingredient}, {fmt_number(instr.amount)}"
        elif instr.op == "serve":
            text = "SERVE"
        else:
            text = f"{instr.op.upper()} {fmt_number(instr.amount * 60)}"
        lines.append((text, instr.lines))
    lines.append(("HALT", code[-1].lines if code else (1,)))
    width = max(COLUMN, *(len(text) + 1 for text, _ in lines))
    return [_line(text, source, width) for text, source in lines]


def _line(text: str, lines: tuple[int, ...], width: int) -> dict:
    return {"text": f"{text:<{width}}; {fmt_lines(lines)}", "lines": sorted(set(lines))}
