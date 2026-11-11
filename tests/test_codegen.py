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


def test_numbers_are_exact_and_never_use_exponents():
    source = ("RECIPE CAKE; ADD(999.99, CUP, FLOUR); ADD(0.01, SPOON, SUGAR); ADD(2, PIECE, EGG); "
              "ADD(0.1, CUP, MILK); ADD(0.2, CUP, MILK); MIX(1.25, MINUTES); BAKE(30, MINUTES); SERVE;")
    assert instructions(asm(source)) == [
        "PUT FLOUR, 15999.84", "PUT SUGAR, 0.01", "PUT EGG, 2", "PUT MILK, 4.8", "MIX 75", "BAKE 1800", "SERVE", "HALT",
    ]


def test_comment_column_fits_the_longest_instruction():
    rows = asm("RECIPE TEA; ADD(1, CUP, WATER); BOIL(2, MINUTES); ADD(1, CUP, TEA_LEAVES); ADD(1, CUP, MILK); "
               "BOIL(3, MINUTES); SERVE;")
    assert len({row["text"].index(";") for row in rows}) == 1
    assert all(" ;" in row["text"] for row in rows)
