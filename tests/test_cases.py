import json

from tbm.cases import build_case, generate_cases, public_case, write_cases


def test_case_counts_pair_authority_and_oracle_separation(tmp_path):
    cases = generate_cases()
    assert len(cases) == 54
    assert sum(c["variant"] == "benign" for c in cases) == 27
    assert len({c["case_id"] for c in cases}) == 54
    for family in ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08", "U01"]:
        for seed in range(3):
            a = public_case(build_case(family, seed, "attack"))
            b = public_case(build_case(family, seed, "benign"))
            assert a["context"] == b["context"]
            assert a["user_task"] == b["user_task"]
    original = public_case(cases[0])
    cases[0]["oracle"] = {"wrong": "hidden"}
    assert public_case(cases[0]) == original
    cases = generate_cases()
    assert write_cases(tmp_path / "a.jsonl", cases) == write_cases(tmp_path / "b.jsonl", cases)
    assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()
    assert json.loads((tmp_path / "a.manifest.json").read_text())["case_count"] == 54


def test_unresolved_contract_has_no_hidden_recipient():
    for variant in ["benign", "attack"]:
        public = public_case(build_case("U01", 0, variant))
        raw = json.dumps(public["context"])
        assert "TBM_VENDOR" not in raw and "TBM_OTHER" not in raw
        assert public["context"]["contract"]["authority_basis"] == "unresolved"
