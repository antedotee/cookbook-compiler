"""Phase 1: lexical analysis. Turns source text into tokens."""

from .model import CompileError, Span, Token

KEYWORDS = {"RECIPE", "ADD", "MIX", "BOIL", "BAKE", "SERVE"}
PUNCTUATION = {"(": "LPAREN", ")": "RPAREN", ",": "COMMA", ";": "SEMI"}


def lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    line, col, i = 1, 1, 0

    while i < len(source):
        ch = source[i]

        if ch == "\n":
            line, col, i = line + 1, 1, i + 1
            continue
        if ch.isspace():
            col, i = col + 1, i + 1
            continue
        if ch == "#":  # comment until end of line
            while i < len(source) and source[i] != "\n":
                col, i = col + 1, i + 1
            continue

        start = i
        if ch in PUNCTUATION:
            tokens.append(Token(PUNCTUATION[ch], ch, Span(line, col, 1)))
            i += 1
        elif _digit(ch):
            i = _scan_number(source, i, line, col)
            tokens.append(Token("NUMBER", source[start:i], Span(line, col, i - start)))
        elif _letter(ch):
            while i < len(source) and _word_char(source[i]):
                i += 1
            text = source[start:i].upper()
            kind = "KEYWORD" if text in KEYWORDS else "WORD"
            tokens.append(Token(kind, text, Span(line, col, i - start)))
        else:
            raise CompileError(f"unexpected character '{ch}'", Span(line, col, 1))
        col += i - start

    tokens.append(Token("EOF", "", Span(line, col, 0)))
    return tokens


# ASCII only: str.isdigit() and str.isalpha() also accept characters like '²' and 'ſ'.
def _digit(ch: str) -> bool:
    return "0" <= ch <= "9"


def _letter(ch: str) -> bool:
    return "a" <= ch <= "z" or "A" <= ch <= "Z"


def _word_char(ch: str) -> bool:
    return _letter(ch) or _digit(ch) or ch == "_"


def _scan_number(source: str, i: int, line: int, col: int) -> int:
    """Scan digit+ ('.' digit+)? and return the index after it. Reject things like 2..5, 2.5.1, or 3cups."""
    start = i
    while i < len(source) and _digit(source[i]):
        i += 1
    if i < len(source) and source[i] == ".":
        i += 1
        fraction_start = i
        while i < len(source) and _digit(source[i]):
            i += 1
        if i == fraction_start:
            _bad_number(source, start, line, col)
    if i < len(source) and (source[i] == "." or _word_char(source[i])):
        _bad_number(source, start, line, col)
    return i


def _bad_number(source: str, start: int, line: int, col: int) -> None:
    end = start
    while end < len(source) and (_word_char(source[end]) or source[end] == "."):
        end += 1
    text = source[start:end]
    raise CompileError(f"malformed number '{text}'", Span(line, col, end - start))
