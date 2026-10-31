import pytest

from compiler.lexer import lex
from compiler.model import CompileError
from conftest import errors, phases


def kinds_and_text(source):
    return [(t.kind, t.text) for t in lex(source)]


def test_tokens_for_a_step():
    assert kinds_and_text("ADD(2, CUP, FLOUR);") == [
        ("KEYWORD", "ADD"), ("LPAREN", "("), ("NUMBER", "2"), ("COMMA", ","), ("WORD", "CUP"),
        ("COMMA", ","), ("WORD", "FLOUR"), ("RPAREN", ")"), ("SEMI", ";"), ("EOF", ""),
    ]


def test_keywords_are_case_insensitive():
    assert kinds_and_text("add serve") == kinds_and_text("ADD SERVE")


def test_decimals_and_positions():
    tokens = lex("RECIPE TEA;\n  ADD(0.5, CUP, MILK);")
    number = next(t for t in tokens if t.kind == "NUMBER")
    assert (number.text, number.span.line, number.span.col) == ("0.5", 2, 7)


def test_comments_are_skipped():
    assert kinds_and_text("# a note\nSERVE;") == [("KEYWORD", "SERVE"), ("SEMI", ";"), ("EOF", "")]


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
