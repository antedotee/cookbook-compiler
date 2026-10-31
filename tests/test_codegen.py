from conftest import GOLDEN_CAKE, PASTA, TEA, instructions, phases


def asm(source):
    return phases(source)["codegen"]["output"]["asm"]


def test_golden_cake_target_code():
    assert instructions(asm(GOLDEN_CAKE)) == [
        "PUT FLOUR, 32", "PUT SUGAR, 16", "PUT EGG, 2", "PUT MILK, 16", "MIX 120", "BAKE 1800", "SERVE", "HALT",
    ]


def test_line_comments():
    lines = [row["text"].split(";")[1].strip() for row in asm(GOLDEN_CAKE)]
    assert lines[0] == "lines 2-3"
    assert lines[2] == "line 5"


def test_pasta_target_code():
    assert instructions(asm(PASTA)) == [
        "PUT WATER, 64", "BOIL 300", "PUT PASTA, 32", "PUT SALT, 1", "BOIL 600", "SERVE", "HALT",
    ]


def test_tea_target_code():
    assert instructions(asm(TEA)) == [
        "PUT WATER, 16", "BOIL 120", "PUT TEA_LEAVES, 1", "PUT MILK, 16", "BOIL 180", "SERVE", "HALT",
    ]
