"""Phase 5: optimization. Three passes, run in order, each returning new code plus a note per change."""

from dataclasses import replace

from .kitchen import UNITS
from .model import IRInstr, fmt_number


def optimize(code: list[IRInstr]) -> tuple[list[IRInstr], list[dict]]:
    notes: list[dict] = []
    for pass_fn in (normalize_units, merge_adds, merge_cooking):
        code, pass_notes = pass_fn(code)
        notes += pass_notes
    return code, notes


def normalize_units(code: list[IRInstr]) -> tuple[list[IRInstr], list[dict]]:
    """Rewrite every amount in its base unit, so 1 CUP becomes 16 SPOON."""
    out, notes = [], []
    for instr in code:
        if instr.op == "add" and UNITS[instr.unit][0] != instr.unit:
            base, factor = UNITS[instr.unit]
            new = replace(instr, amount=instr.amount * factor, unit=base)
            notes.append(_note("normalize units", f"{instr.ingredient}: {fmt_number(instr.amount)} {instr.unit} "
                                                  f"becomes {fmt_number(new.amount)} {base}", instr))
            instr = new
        out.append(instr)
    return out, notes


def merge_adds(code: list[IRInstr]) -> tuple[list[IRInstr], list[dict]]:
    """Merge back-to-back adds of the same ingredient into one."""
    return _merge_adjacent(code, "merge adds", lambda a, b: a.op == b.op == "add" and a.ingredient == b.ingredient,
                           lambda m: f"{m.ingredient}: adds merged into {fmt_number(m.amount)} {m.unit}")


def merge_cooking(code: list[IRInstr]) -> tuple[list[IRInstr], list[dict]]:
    """Merge back-to-back runs of the same cooking step into one longer step."""
    return _merge_adjacent(code, "merge cooking", lambda a, b: a.op == b.op and a.op in ("mix", "boil", "bake"),
                           lambda m: f"{m.op} steps merged into {fmt_number(m.amount)} {m.unit}")


def _merge_adjacent(code, pass_name, mergeable, describe):
    out: list[IRInstr] = []
    merged_into: set[int] = set()
    for instr in code:
        if out and mergeable(out[-1], instr):
            prev = out[-1]
            out[-1] = replace(prev, amount=prev.amount + instr.amount, lines=prev.lines + instr.lines)
            merged_into.add(len(out) - 1)
        else:
            out.append(instr)
    notes = [_note(pass_name, describe(out[i]), out[i]) for i in sorted(merged_into)]
    return out, notes


def _note(pass_name: str, message: str, instr: IRInstr) -> dict:
    return {"pass": pass_name, "message": message, "lines": sorted(set(instr.lines))}
