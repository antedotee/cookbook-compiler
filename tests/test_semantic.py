from pathlib import Path

import pytest

from conftest import GOLDEN_CAKE, PASTA, TEA, errors, phases

CAKE_ADDS = "ADD(1, CUP, FLOUR); ADD(1, CUP, SUGAR); ADD(2, PIECE, EGG); ADD(1, CUP, MILK);"


def cake(body: str) -> str:
    return f"RECIPE CAKE; {body}"


@pytest.mark.parametrize("source", [GOLDEN_CAKE, PASTA, TEA])
def test_valid_dishes_pass_every_check(source):
    phase = phases(source)["semantic"]
    assert phase["status"] == "ok"
    assert all(check["ok"] for check in phase["output"]["checks"])


def test_symbol_table():
    symbols = {s["name"]: s for s in phases(GOLDEN_CAKE)["semantic"]["output"]["symbols"]}
    assert symbols["CAKE"]["kind"] == "dish"
    assert (symbols["FLOUR"]["total"], symbols["FLOUR"]["unit"], symbols["FLOUR"]["first_line"]) == ("2", "CUP", 2)
    assert (symbols["EGG"]["total"], symbols["EGG"]["unit"]) == ("2", "PIECE")


def test_symbol_table_converts_mixed_units_to_base():
    source = cake("ADD(1, CUP, FLOUR); ADD(2, SPOON, FLOUR); ADD(1, CUP, SUGAR); ADD(2, PIECE, EGG); "
                  "ADD(1, CUP, MILK); MIX(1, MINUTES); BAKE(30, MINUTES); SERVE;")
    flour = next(s for s in phases(source)["semantic"]["output"]["symbols"] if s["name"] == "FLOUR")
    assert (flour["total"], flour["unit"]) == ("18", "SPOON")


@pytest.mark.parametrize("source, message", [
    ("RECIPE CAK; SERVE;", "unknown dish 'CAK' (did you mean CAKE?), choose one of CAKE, PASTA, TEA"),
    (cake("ADD(1, CUP, FLOWER); SERVE;"), "unknown ingredient 'FLOWER' (did you mean FLOUR?)"),
    (cake("ADD(2, CUP, EGG);"), "EGG is measured in PIECE, not CUP"),
    (cake("ADD(2, LITRE, MILK);"), "unknown unit 'LITRE', use one of CUP, SPOON, PIECE"),
    (cake("ADD(1.5, PIECE, EGG);"), "EGG must be a whole number of PIECE, not 1.5"),
    (cake("ADD(0, CUP, FLOUR);"), "the amount of FLOUR must be greater than 0 and at most 1000"),
    (cake(CAKE_ADDS + "MIX(0, MINUTES);"), "MIX time must be between 1 and 180 minutes, not 0"),
    (cake(CAKE_ADDS + "MIX(200, MINUTES);"), "MIX time must be between 1 and 180 minutes, not 200"),
    (cake(CAKE_ADDS + "MIX(2, SECONDS);"), "MIX time must be in MINUTES, not SECONDS"),
    (cake("ADD(1, CUP, FLOUR); ADD(1, CUP, SUGAR); ADD(1, CUP, MILK); MIX(1, MINUTES);"),
     "MIX needs EGG added first"),
    (cake("ADD(1, CUP, WATER);"), "WATER does not belong in CAKE"),
    (cake(CAKE_ADDS + "MIX(1, MINUTES); BAKE(30, MINUTES); SERVE; SERVE;"), "nothing can come after SERVE on line 1"),
    (cake(CAKE_ADDS + "MIX(1, MINUTES); BAKE(30, MINUTES);"), "the recipe must end with SERVE;"),
    (cake(CAKE_ADDS + "MIX(1, MINUTES); SERVE;"), "CAKE is served before BAKE"),
    ("RECIPE TEA; ADD(1, CUP, WATER); BOIL(2, MINUTES); ADD(1, CUP, MILK); ADD(1, SPOON, TEA_LEAVES); "
     "BOIL(2, MINUTES); BOIL(2, MINUTES); SERVE;", None),
])
def test_rules(source, message):
    result = phases(source)["semantic"]
    if message is None:
        assert result["status"] == "ok", result["errors"]
    else:
        assert message in [e["message"] for e in result["errors"]]


def test_collects_every_error_and_marks_failed_checks():
    source = "RECIPE CAKE;\nADD(2, CUP, EGG);\nBAKE(30, MINUTES);\nSERVE;\nSERVE;"
    found = errors(source, "semantic")
    assert len(found) >= 3
    checks = {c["rule"]: c for c in phases(source)["semantic"]["output"]["checks"]}
    assert not checks["Every unit suits its ingredient or step"]["ok"]
    assert not checks["Steps follow the dish's order"]["ok"]
    assert checks["Steps follow the dish's order"]["lines"] == [3]
    assert checks["The dish is one the kitchen knows"]["ok"]


def test_semantic_error_skips_code_generation():
    result = phases(cake("ADD(2, CUP, EGG);"))
    assert [result[p]["status"] for p in ("ir", "optimizer", "codegen")] == ["skipped"] * 3


def order_errors(source):
    return [e["message"] for e in phases(source)["semantic"]["errors"]]


@pytest.mark.parametrize("body, expected", [
    ("BAKE(30, MINUTES); SERVE;", "MIX is missing before BAKE"),
    ("BAKE(30, MINUTES); MIX(1, MINUTES); SERVE;", "MIX must come before BAKE, swap these two steps"),
    ("BOIL(3, MINUTES); BAKE(30, MINUTES); SERVE;", "BOIL is not a step of CAKE, the step here is MIX"),
    ("MIX(1, MINUTES); BOIL(3, MINUTES); MIX(1, MINUTES); BAKE(30, MINUTES); SERVE;", "BOIL is not a step of CAKE"),
    ("MIX(1, MINUTES); SERVE;", "CAKE is served before BAKE"),
    ("SERVE; MIX(1, MINUTES); BAKE(30, MINUTES); SERVE;", "SERVE comes too early, CAKE still needs MIX and BAKE"),
    ("MIX(1, MINUTES); BAKE(30, MINUTES); SERVE; SERVE; SERVE;", "nothing can come after SERVE on line 1 (2 steps follow it)"),
])
def test_one_ordering_mistake_gives_one_error(body, expected):
    assert order_errors(cake(CAKE_ADDS + body)) == [expected]


VALID_ORDERS = {
    "CAKE": [("ADD", "FLOUR"), ("ADD", "SUGAR"), ("ADD", "EGG"), ("ADD", "MILK"), ("COOK", "MIX"), ("COOK", "BAKE"), ("SERVE", "")],
    "PASTA": [("ADD", "WATER"), ("COOK", "BOIL"), ("ADD", "PASTA"), ("ADD", "SALT"), ("COOK", "BOIL"), ("SERVE", "")],
    "TEA": [("ADD", "WATER"), ("COOK", "BOIL"), ("ADD", "TEA_LEAVES"), ("ADD", "MILK"), ("COOK", "BOIL"), ("SERVE", "")],
}
ALPHABET = [("ADD", n) for n in ("FLOUR", "SUGAR", "EGG", "MILK", "WATER", "PASTA", "SALT", "TEA_LEAVES")] + [
    ("COOK", v) for v in ("MIX", "BOIL", "BAKE")] + [("SERVE", "")]


def write(dish, seq):
    text = {"ADD": lambda n: f"ADD({2 if n == 'EGG' else 1}, {'PIECE' if n == 'EGG' else 'CUP'}, {n});",
            "COOK": lambda v: f"{v}(1, MINUTES);", "SERVE": lambda _: "SERVE;"}
    return f"RECIPE {dish};\n" + "\n".join(text[kind](name) for kind, name in seq)


def single_mistakes(seq):
    for i in range(len(seq)):
        yield seq[:i] + seq[i + 1:]
        yield from (seq[:i] + [a] + seq[i + 1:] for a in ALPHABET if a != seq[i])
        if i + 1 < len(seq):
            yield seq[:i] + [seq[i + 1], seq[i]] + seq[i + 2:]
    for i in range(len(seq) + 1):
        yield from (seq[:i] + [a] + seq[i:] for a in ALPHABET)


@pytest.mark.parametrize("dish", VALID_ORDERS)
def test_every_single_mistake_gives_at_most_one_order_error(dish):
    """Delete, replace, insert, or swap any one step of a valid recipe. Errors land on one line only."""
    for seq in single_mistakes(VALID_ORDERS[dish]):
        result = phases(write(dish, seq))["semantic"]
        assert len({e["line"] for e in result["errors"]}) <= 1, (seq, [e["message"] for e in result["errors"]])


def test_misspelled_ingredient_is_reported_once():
    source = cake("ADD(1, CUP, FLOWER); ADD(1, CUP, SUGAR); ADD(2, PIECE, EGG); ADD(1, CUP, MILK); "
                  "MIX(1, MINUTES); BAKE(30, MINUTES); SERVE;")
    assert order_errors(source) == ["unknown ingredient 'FLOWER' (did you mean FLOUR?)"]


def test_misplaced_steps_are_explained_as_one_move():
    pasta = ("RECIPE PASTA; ADD(4, CUP, WATER); ADD(2, CUP, PASTA); BOIL(5, MINUTES); "
             "ADD(1, SPOON, SALT); BOIL(10, MINUTES); SERVE;")
    assert order_errors(pasta) == ["BOIL must come before adding PASTA, swap these two steps"]
    late_egg = cake("ADD(1, CUP, FLOUR); ADD(1, CUP, SUGAR); ADD(1, CUP, MILK); MIX(1, MINUTES); "
                    "ADD(2, PIECE, EGG); BAKE(30, MINUTES); SERVE;")
    assert order_errors(late_egg) == ["adding EGG must come before MIX, swap these two steps"]


def test_foreign_ingredient_in_place_of_a_needed_one_is_one_error():
    source = cake("ADD(1, CUP, WATER); ADD(1, CUP, SUGAR); ADD(2, PIECE, EGG); ADD(1, CUP, MILK); "
                  "MIX(1, MINUTES); BAKE(30, MINUTES); SERVE;")
    assert order_errors(source) == ["WATER does not belong in CAKE"]


def test_semantic_example_reports_its_three_mistakes():
    source = (Path(__file__).parent.parent / "examples" / "6_semantic_error.ck").read_text()
    assert len(order_errors(source)) == 3


@pytest.mark.parametrize("amount", ["9" * 400, "1001"])
def test_huge_amounts_are_range_errors_not_crashes(amount):
    for unit, name in (("CUP", "FLOUR"), ("PIECE", "EGG")):
        messages = order_errors(cake(f"ADD({amount}, {unit}, {name});"))
        assert f"the amount of {name} must be greater than 0 and at most 1000" in messages


def test_huge_duration_is_a_range_error():
    assert "MIX time must be between 1 and 180 minutes, not " + "9" * 400 in order_errors(cake(CAKE_ADDS + f"MIX({'9' * 400}, MINUTES);"))


def test_at_most_two_decimal_places():
    assert "amounts can have at most 2 decimal places, not 1.005" in order_errors(cake("ADD(1.005, CUP, FLOUR);"))
    assert "times can have at most 2 decimal places, not 1.125" in order_errors(cake(CAKE_ADDS + "MIX(1.125, MINUTES);"))


def test_unknown_dish_leaves_dependent_rules_unchecked():
    checks = {c["rule"]: c["ok"] for c in phases("RECIPE PIZZA; SERVE;")["semantic"]["output"]["checks"]}
    assert checks["Steps follow the dish's order"] is None
    assert checks["The dish is one the kitchen knows"] is False
