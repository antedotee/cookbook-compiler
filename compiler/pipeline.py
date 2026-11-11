"""Runs the six phases in order and returns one JSON-ready result for the web page."""

from __future__ import annotations

from . import codegen, ir, optimizer
from .lexer import lex
from .model import CompileError, Diagnostic
from .parser import parse, to_tree
from .semantic import analyze

PHASES = [
    ("lexer", "1. Lexical analysis"),
    ("parser", "2. Syntax analysis"),
    ("semantic", "3. Semantic analysis"),
    ("ir", "4. Intermediate code"),
    ("optimizer", "5. Optimization"),
    ("codegen", "6. Target code"),
]


def compile_recipe(source: str) -> dict:
    results: list[dict] = []

    def done(output: dict, errors: list[Diagnostic] = ()) -> None:
        phase_id, title = PHASES[len(results)]
        results.append({
            "id": phase_id,
            "title": title,
            "status": "error" if errors else "ok",
            "output": output,
            "errors": [error.to_json() for error in errors],
        })

    try:
        tokens = lex(source)
        done({"tokens": [{"kind": t.kind, "text": t.text, "line": t.span.line, "col": t.span.col} for t in tokens]})

        recipe = parse(tokens)
        done({"tree": to_tree(recipe)})

        semantic = analyze(recipe)
        done({"symbols": semantic.symbols, "checks": semantic.checks}, semantic.errors)
        if not semantic.errors:
            code = ir.generate(recipe)
            done({"code": ir.render(code)})

            optimized, notes = optimizer.optimize(code)
            done({"before": ir.render(code), "after": ir.render(optimized), "notes": notes})

            done({"asm": codegen.generate(optimized)})
    except CompileError as error:
        done(None, [error.diagnostic])

    for phase_id, title in PHASES[len(results):]:
        results.append({"id": phase_id, "title": title, "status": "skipped", "output": None, "errors": []})
    return {"source": source, "phases": results}
