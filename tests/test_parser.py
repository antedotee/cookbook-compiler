import pytest

from compiler.lexer import lex
from compiler.model import AddStep, ServeStep, TimedStep
from compiler.parser import parse
from conftest import GOLDEN_CAKE, PASTA, TEA, errors, phases


def test_builds_ast_for_cake():
    recipe = parse(lex(GOLDEN_CAKE))
    assert recipe.dish.text == "CAKE"
    assert [type(s) for s in recipe.steps] == [AddStep] * 5 + [TimedStep] * 3 + [ServeStep]
    first = recipe.steps[0]
    assert (first.amount.value, first.unit.text, first.ingredient.text) == (1.0, "CUP", "FLOUR")
    assert recipe.steps[-2].verb == "BAKE" and recipe.steps[-2].duration.value == 30


@pytest.mark.parametrize("source, verbs", [
    (PASTA, ["ADD", "BOIL", "ADD", "ADD", "BOIL", "SERVE"]),
    (TEA, ["ADD", "BOIL", "ADD", "ADD", "BOIL", "SERVE"]),
])
def test_builds_ast_for_other_dishes(source, verbs):
    steps = parse(lex(source)).steps
    assert [getattr(s, "verb", "ADD" if isinstance(s, AddStep) else "SERVE") for s in steps] == verbs


def test_tree_has_header_and_steps():
    tree = phases(GOLDEN_CAKE)["parser"]["output"]["tree"]
    assert tree["label"] == "Recipe"
    header, steps = tree["children"]
    assert header["children"][0]["label"] == "dish CAKE"
    assert [c["label"] for c in steps["children"][0]["children"]] == ["amount 1", "unit CUP", "ingredient FLOUR"]
    assert steps["lines"] == list(range(2, 11))


def test_missing_semicolon_points_at_the_line_that_needs_it():
    source = "RECIPE TEA;\nADD(1, CUP, WATER)\nBOIL(2, MINUTES);\nSERVE;"
    phase = phases(source)["parser"]
    assert phase["errors"][0]["message"] == "expected ';' after the ADD step, but found 'BOIL'"
    assert phase["errors"][0]["line"] == 2


def test_missing_close_paren():
    assert errors("RECIPE TEA; ADD(1, CUP, WATER;", "parser") == ["expected ',' or ')' in ADD(...), but found ';'"]


def test_wrong_argument_count():
    assert errors("RECIPE TEA; ADD(1, WATER);", "parser") == [
        "ADD needs 3 arguments: amount, unit, ingredient, but got 2"
    ]
    assert errors("RECIPE TEA; BOIL(2);", "parser") == ["BOIL needs 2 arguments: minutes, unit, but got 1"]


def test_argument_kinds():
    assert errors("RECIPE TEA; ADD(CUP, 1, WATER);", "parser") == [
        "the amount in ADD must be a number, but found 'CUP'"
    ]


def test_missing_header():
    assert errors("ADD(1, CUP, WATER);", "parser") == [
        "a recipe must start with 'RECIPE <dish>;', but found 'ADD'"
    ]


def test_serve_takes_no_arguments():
    assert errors("RECIPE TEA; SERVE();", "parser") == ["SERVE takes no arguments, write 'SERVE;'"]


def test_empty_recipe():
    assert errors("# nothing yet\n", "parser") == ["the recipe is empty, start with 'RECIPE <dish>;'"]


def test_keyword_in_argument_is_named():
    assert errors("RECIPE CAKE; ADD(2, CUP, MIX);", "parser") == ["'MIX' is a keyword and cannot be a value in ADD(...)"]


def test_unclosed_step_at_end_points_after_last_token():
    error = phases("RECIPE CAKE;\nADD(1, CUP, FLOUR\n\n\n")["parser"]["errors"][0]
    assert (error["line"], error["col"]) == (2, 18)
