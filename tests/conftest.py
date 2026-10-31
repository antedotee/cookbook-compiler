import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler import compile_recipe  # noqa: E402

GOLDEN_CAKE = """RECIPE CAKE;
ADD(1, CUP, FLOUR);
ADD(1, CUP, FLOUR);
ADD(1, CUP, SUGAR);
ADD(2, PIECE, EGG);
ADD(1, CUP, MILK);
MIX(1, MINUTES);
MIX(1, MINUTES);
BAKE(30, MINUTES);
SERVE;
"""

PASTA = """RECIPE PASTA;
ADD(4, CUP, WATER);
BOIL(5, MINUTES);
ADD(2, CUP, PASTA);
ADD(1, SPOON, SALT);
BOIL(10, MINUTES);
SERVE;
"""

TEA = """RECIPE TEA;
ADD(1, CUP, WATER);
BOIL(2, MINUTES);
ADD(1, SPOON, TEA_LEAVES);
ADD(1, CUP, MILK);
BOIL(3, MINUTES);
SERVE;
"""


def phases(source: str) -> dict:
    return {p["id"]: p for p in compile_recipe(source)["phases"]}


def errors(source: str, phase_id: str) -> list[str]:
    phase = phases(source)[phase_id]
    assert phase["status"] == "error", f"{phase_id} should fail but was {phase['status']}"
    return [e["message"] for e in phase["errors"]]


def instructions(rows: list[dict]) -> list[str]:
    """Rendered code without the trailing '; line N' comment."""
    return [row["text"].split(";")[0].strip() for row in rows]


@pytest.fixture
def client():
    from app import app

    return app.test_client()
