"""Data passed between compiler phases."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Span:
    line: int
    col: int
    length: int = 1


@dataclass(frozen=True)
class Diagnostic:
    message: str
    span: Span

    def to_json(self) -> dict:
        return {"message": self.message, "line": self.span.line, "col": self.span.col, "length": self.span.length}


class CompileError(Exception):
    def __init__(self, message: str, span: Span):
        super().__init__(message)
        self.diagnostic = Diagnostic(message, span)


# Phase 1 output

@dataclass(frozen=True)
class Token:
    kind: str  # KEYWORD, WORD, NUMBER, LPAREN, RPAREN, COMMA, SEMI, EOF
    text: str
    span: Span


# Phase 2 output

@dataclass(frozen=True)
class Name:
    text: str
    span: Span


@dataclass(frozen=True)
class Number:
    value: float
    text: str
    span: Span


@dataclass(frozen=True)
class AddStep:
    amount: Number
    unit: Name
    ingredient: Name
    span: Span


@dataclass(frozen=True)
class TimedStep:
    verb: str  # MIX, BOIL, BAKE
    duration: Number
    unit: Name
    span: Span


@dataclass(frozen=True)
class ServeStep:
    span: Span


Step = AddStep | TimedStep | ServeStep


@dataclass(frozen=True)
class Recipe:
    dish: Name
    steps: list[Step]
    span: Span


# Phases 4 and 5 output

@dataclass(frozen=True)
class IRInstr:
    op: str  # add, mix, boil, bake, serve
    amount: float = 0
    unit: str = ""
    ingredient: str = ""
    lines: tuple[int, ...] = field(default_factory=tuple)


def fmt_number(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:g}"


def fmt_lines(lines: tuple[int, ...]) -> str:
    ordered = sorted(set(lines))
    if len(ordered) == 1:
        return f"line {ordered[0]}"
    if ordered == list(range(ordered[0], ordered[-1] + 1)):
        return f"lines {ordered[0]}-{ordered[-1]}"
    return "lines " + ", ".join(map(str, ordered))
