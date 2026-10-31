"""Phase 6: target code. Pseudo-assembly for an imaginary kitchen machine.

    PUT <ingredient>, <amount>   amount in SPOON or PIECE
    MIX | BOIL | BAKE <seconds>
    SERVE
    HALT
"""

from .model import IRInstr, fmt_lines, fmt_number

COLUMN = 18


def generate(code: list[IRInstr]) -> list[dict]:
    asm = []
    for instr in code:
        if instr.op == "add":
            text = f"PUT {instr.ingredient}, {fmt_number(instr.amount)}"
        elif instr.op == "serve":
            text = "SERVE"
        else:
            text = f"{instr.op.upper()} {round(instr.amount * 60)}"
        asm.append(_line(text, instr.lines))
    asm.append(_line("HALT", code[-1].lines if code else (1,)))
    return asm


def _line(text: str, lines: tuple[int, ...]) -> dict:
    return {"text": f"{text:<{COLUMN}}; {fmt_lines(lines)}", "lines": sorted(set(lines))}
