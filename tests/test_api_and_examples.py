import pytest

from compiler.kitchen import vocab
from conftest import GOLDEN_CAKE

PHASE_IDS = ["lexer", "parser", "semantic", "ir", "optimizer", "codegen"]
EXPECTED = {
    "1_cake": None, "2_pasta": None, "3_tea": None,
    "4_lexical_error": "lexer", "5_syntax_error": "parser", "6_semantic_error": "semantic",
}


def test_compile_contract(client):
    body = client.post("/api/compile", json={"source": GOLDEN_CAKE}).get_json()
    assert body["source"] == GOLDEN_CAKE
    assert [p["id"] for p in body["phases"]] == PHASE_IDS
    for phase in body["phases"]:
        assert set(phase) == {"id", "title", "status", "output", "errors"}
        assert phase["status"] == "ok"


def test_every_output_item_knows_its_source_lines(client):
    phases = {p["id"]: p["output"] for p in client.post("/api/compile", json={"source": GOLDEN_CAKE}).get_json()["phases"]}
    items = phases["ir"]["code"] + phases["optimizer"]["after"] + phases["optimizer"]["notes"] + phases["codegen"]["asm"]
    assert all(item["lines"] for item in items)
    assert all(t["line"] >= 1 for t in phases["lexer"]["tokens"])


def test_any_input_gets_six_phases(client):
    body = client.post("/api/compile", json={"source": ""}).get_json()
    assert [p["status"] for p in body["phases"]] == ["ok", "error"] + ["skipped"] * 4


@pytest.mark.parametrize("body", [{"nope": 1}, ["x"], "text", 5])
def test_bad_request(client, body):
    assert client.post("/api/compile", json=body).status_code == 400


def test_vocab_matches_kitchen(client):
    assert client.get("/api/vocab").get_json() == vocab()


@pytest.mark.parametrize("example_id, failing_phase", EXPECTED.items())
def test_examples_fail_only_where_intended(client, example_id, failing_phase):
    examples = {e["id"]: e for e in client.get("/api/examples").get_json()}
    assert set(examples) == set(EXPECTED)
    phases = client.post("/api/compile", json={"source": examples[example_id]["source"]}).get_json()["phases"]
    statuses = {p["id"]: p["status"] for p in phases}
    if failing_phase is None:
        assert set(statuses.values()) == {"ok"}
    else:
        assert statuses[failing_phase] == "error"
        assert all(statuses[p] == "ok" for p in PHASE_IDS[:PHASE_IDS.index(failing_phase)])
