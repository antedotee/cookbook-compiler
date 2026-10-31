from compiler.model import IRInstr
from compiler.optimizer import optimize
from conftest import GOLDEN_CAKE, PASTA, instructions, phases


def test_ir_is_one_instruction_per_step_in_source_units():
    code = phases(GOLDEN_CAKE)["ir"]["output"]["code"]
    assert [row["text"] for row in code] == [
        "t1 = add FLOUR, 1 CUP", "t2 = add FLOUR, 1 CUP", "t3 = add SUGAR, 1 CUP", "t4 = add EGG, 2 PIECE",
        "t5 = add MILK, 1 CUP", "t6 = mix 1 MIN", "t7 = mix 1 MIN", "t8 = bake 30 MIN", "t9 = serve",
    ]
    assert [row["lines"] for row in code] == [[n] for n in range(2, 11)]


def test_optimizer_shows_before_after_and_notes():
    out = phases(GOLDEN_CAKE)["optimizer"]["output"]
    assert len(out["before"]) == 9
    assert instructions(out["after"]) == [
        "t1 = add FLOUR, 32 SPOON", "t2 = add SUGAR, 16 SPOON", "t3 = add EGG, 2 PIECE",
        "t4 = add MILK, 16 SPOON", "t5 = mix 2 MIN", "t6 = bake 30 MIN", "t7 = serve",
    ]
    passes = [note["pass"] for note in out["notes"]]
    assert passes.count("merge adds") == 1 and passes.count("merge cooking") == 1
    assert out["after"][0]["lines"] == [2, 3]


def test_cup_and_spoon_fold_into_spoons():
    code, _ = optimize([IRInstr("add", 1, "CUP", "SUGAR", (2,)), IRInstr("add", 2, "SPOON", "SUGAR", (3,))])
    assert code == [IRInstr("add", 18, "SPOON", "SUGAR", (2, 3))]


def test_non_adjacent_steps_never_merge():
    after = phases(PASTA)["optimizer"]["output"]["after"]
    assert sum(row["text"].endswith("boil 5 MIN") or row["text"].endswith("boil 10 MIN") for row in after) == 2
