"""Phase 2: syntax analysis. A recursive-descent parser for this grammar:

    recipe = "RECIPE" IDENTIFIER ";" { step ";" } EOF ;
    step   = "ADD" "(" CONSTANT "," IDENTIFIER "," IDENTIFIER ")"
           | ("MIX" | "BOIL" | "BAKE") "(" CONSTANT "," IDENTIFIER ")"
           | "SERVE" ;
"""

from .model import AddStep, CompileError, Name, Number, Recipe, ServeStep, Span, Step, TimedStep, Token

STEP_VERBS = ("ADD", "MIX", "BOIL", "BAKE", "SERVE")
ARGUMENTS = {
    "ADD": ("amount", "unit", "ingredient"),
    "MIX": ("minutes", "unit"),
    "BOIL": ("minutes", "unit"),
    "BAKE": ("minutes", "unit"),
}


def parse(tokens: list[Token]) -> Recipe:
    return _Parser(tokens).recipe()


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        if token.kind != "EOF":
            self.pos += 1
        return token

    def at(self, punctuator: str) -> bool:
        token = self.peek()
        return token.kind == "PUNCTUATOR" and token.text == punctuator

    def expect(self, kind: str, message: str, text: str | None = None) -> Token:
        token = self.peek()
        if token.kind != kind or (text is not None and token.text != text):
            raise CompileError(f"{message}, but found {_describe(token)}", token.span)
        return self.advance()

    def recipe(self) -> Recipe:
        first = self.peek()
        if not (first.kind == "KEYWORD" and first.text == "RECIPE"):
            raise CompileError(f"a recipe must start with 'RECIPE <dish>;', but found {_describe(first)}", first.span)
        self.advance()
        dish = self.expect("IDENTIFIER", "expected a dish name (an identifier) after RECIPE")
        self.expect_semicolon(f"'RECIPE {dish.text}'")

        steps: list[Step] = []
        while self.peek().kind != "EOF":
            step = self.step()
            steps.append(step)
            self.expect_semicolon(f"the {_verb_of(step)} step")
        return Recipe(Name(dish.text, dish.span), steps, first.span)

    def expect_semicolon(self, after: str) -> None:
        """Report a missing ';' at the end of the previous token, where the user has to type it."""
        if self.at(";"):
            self.advance()
            return
        last = self.tokens[self.pos - 1]
        raise CompileError(
            f"expected ';' after {after} on line {last.span.line}, but found {_describe(self.peek())}",
            Span(last.span.line, last.span.col + last.span.length, 1),
        )

    def step(self) -> Step:
        token = self.peek()
        if token.kind != "KEYWORD" or token.text not in STEP_VERBS:
            if token.kind == "KEYWORD" and token.text == "RECIPE":
                raise CompileError("RECIPE can only appear once, at the start", token.span)
            raise CompileError(f"expected a step ({', '.join(STEP_VERBS)}), but found {_describe(token)}", token.span)
        self.advance()

        if token.text == "SERVE":
            if self.at("("):
                raise CompileError("SERVE takes no arguments, write 'SERVE;'", self.peek().span)
            return ServeStep(token.span)

        args = self.arguments(token)
        if token.text == "ADD":
            amount, unit, ingredient = args
            return AddStep(amount, unit, ingredient, token.span)
        duration, unit = args
        return TimedStep(token.text, duration, unit, token.span)

    def arguments(self, verb: Token) -> list:
        """Parse '(' arg {',' arg} ')' and check the count and kind of each argument against ARGUMENTS."""
        names = ARGUMENTS[verb.text]
        usage = f"{verb.text} needs {len(names)} arguments: {', '.join(names)}"
        self.expect("PUNCTUATOR", f"expected '(' after {verb.text} ({usage})", "(")

        found: list[Token] = []
        if not self.at(")"):
            while True:
                token = self.peek()
                if token.kind not in ("CONSTANT", "IDENTIFIER"):
                    raise CompileError(f"expected a value in {verb.text}(...), but found {_describe(token)}", token.span)
                found.append(self.advance())
                if self.at(","):
                    self.advance()
                    continue
                if self.at(")"):
                    break
                raise CompileError(f"expected ',' or ')' in {verb.text}(...), but found {_describe(self.peek())}", self.peek().span)
        close = self.advance()

        if len(found) != len(names):
            same_line = close.span.line == verb.span.line
            length = close.span.col + 1 - verb.span.col if same_line else len(verb.text)
            raise CompileError(f"{usage}, but got {len(found)}", Span(verb.span.line, verb.span.col, length))

        args = []
        for index, (name, token) in enumerate(zip(names, found)):
            wants_number = index == 0
            if wants_number and token.kind != "CONSTANT":
                raise CompileError(f"the {name} in {verb.text} must be a number, but found '{token.text}'", token.span)
            if not wants_number and token.kind != "IDENTIFIER":
                raise CompileError(f"the {name} in {verb.text} must be an identifier, but found '{token.text}'", token.span)
            args.append(Number(float(token.text), token.text, token.span) if wants_number else Name(token.text, token.span))
        return args


def _describe(token: Token) -> str:
    return "the end of the recipe" if token.kind == "EOF" else f"'{token.text}'"


def _verb_of(step: Step) -> str:
    return {AddStep: "ADD", ServeStep: "SERVE"}.get(type(step)) or step.verb


def to_tree(recipe: Recipe) -> dict:
    """The parse tree as {label, lines, children} for display."""

    def node(label: str, span: Span, children=()) -> dict:
        kids = list(children)
        lines = sorted({span.line, *(line for kid in kids for line in kid["lines"])})
        return {"label": label, "lines": lines, "children": kids}

    def step_node(step: Step) -> dict:
        if isinstance(step, AddStep):
            return node("ADD", step.span, [
                node(f"amount {step.amount.text}", step.amount.span),
                node(f"unit {step.unit.text}", step.unit.span),
                node(f"ingredient {step.ingredient.text}", step.ingredient.span),
            ])
        if isinstance(step, TimedStep):
            return node(step.verb, step.span, [
                node(f"time {step.duration.text}", step.duration.span),
                node(f"unit {step.unit.text}", step.unit.span),
            ])
        return node("SERVE", step.span)

    header = node("Header", recipe.span, [node(f"dish {recipe.dish.text}", recipe.dish.span)])
    steps = [step_node(step) for step in recipe.steps]
    steps_span = recipe.steps[0].span if recipe.steps else recipe.span
    return node("Recipe", recipe.span, [header, node("Steps", steps_span, steps)])
