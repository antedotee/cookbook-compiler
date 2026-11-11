import pytest

from compiler.lexer import lex
from compiler.model import CompileError
from conftest import errors, phases


def kinds_and_text(source):
    return [(t.kind, t.text) for t in lex(source)]


def test_tokens_for_a_step():
    assert kinds_and_text("ADD(2, CUP, FLOUR);") == [
        ("KEYWORD", "ADD"), ("PUNCTUATOR", "("), ("CONSTANT", "2"), ("PUNCTUATOR", ","), ("IDENTIFIER", "CUP"),
        ("PUNCTUATOR", ","), ("IDENTIFIER", "FLOUR"), ("PUNCTUATOR", ")"), ("PUNCTUATOR", ";"), ("EOF", ""),
    ]


def test_keywords_are_case_insensitive():
    assert kinds_and_text("add serve") == kinds_and_text("ADD SERVE")


def test_decimals_and_positions():
    tokens = lex("RECIPE TEA;\n  ADD(0.5, CUP, MILK);")
    number = next(t for t in tokens if t.kind == "CONSTANT")
    assert (number.text, number.span.line, number.span.col) == ("0.5", 2, 7)


def test_comments_are_skipped():
    assert kinds_and_text("# a note\nSERVE;") == [("KEYWORD", "SERVE"), ("PUNCTUATOR", ";"), ("EOF", "")]


def test_illegal_character_reports_line_and_column():
    with pytest.raises(CompileError) as caught:
        lex("RECIPE CAKE;\nADD(1, CUP, FLOUR) @")
    d = caught.value.diagnostic
    assert (d.message, d.span.line, d.span.col) == ("unexpected character '@'", 2, 20)


@pytest.mark.parametrize("bad", ["2..5", "2.5.1", "3cups", "4."])
def test_malformed_numbers(bad):
    with pytest.raises(CompileError) as caught:
        lex(f"ADD({bad}, CUP, FLOUR);")
    assert caught.value.diagnostic.message == f"malformed number '{bad}'"
    assert caught.value.diagnostic.span.col == 5


def test_lexer_error_skips_later_phases():
    result = phases("RECIPE CAKE; $")
    assert result["lexer"]["status"] == "error"
    assert all(result[p]["status"] == "skipped" for p in ("parser", "semantic", "ir", "optimizer", "codegen"))
    assert errors("RECIPE CAKE; $", "lexer") == ["unexpected character '$'"]


@pytest.mark.parametrize("text, bad", [("ADD(², CUP, FLOUR);", "²"), ("ADD(١٢, CUP, FLOUR);", "١"), ("ſERVE;", "ſ")])
def test_only_ascii_letters_and_digits(text, bad):
    with pytest.raises(CompileError) as caught:
        lex(text)
    assert caught.value.diagnostic.message == f"unexpected character '{bad}'"


def test_superscript_after_digit_is_lexical_error():
    assert errors("RECIPE CAKE; MIX(1², MINUTES);", "lexer") == ["unexpected character '²'"]


def test_names_that_are_not_keywords_are_identifiers():
    assert kinds_and_text("RECIPE cake; add") == [
        ("KEYWORD", "RECIPE"), ("IDENTIFIER", "CAKE"), ("PUNCTUATOR", ";"), ("KEYWORD", "ADD"), ("EOF", ""),
    ]


def test_lone_carriage_return_is_a_line_break():
    assert [t.span.line for t in lex("RECIPE CAKE;\rSERVE;")][-2] == 2
    assert [t.span.line for t in lex("RECIPE CAKE;\r\nSERVE;")][-2] == 2


def test_invisible_characters_are_named():
    assert errors("RECIPE CAKE;\u200b", "lexer") == ["unexpected character U+200B (zero width space)"]
