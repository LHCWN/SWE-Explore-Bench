"""The per-language benchmark is built from the released file without network access."""
import json

import pytest
from typer.testing import CliRunner

from build_language_bench import (
    LANGUAGE_REPOS, app, attach_issues, get_org_repo, select_instances,
)


@pytest.mark.parametrize("instance_id,expected", [
    ("fmtlib__fmt-3901", "fmtlib/fmt"),
    ("valkey-io__valkey-790", "valkey-io/valkey"),
    ("micropython__micropython-13039", "micropython/micropython"),
    ("no-org-here-1", ""),
])
def test_org_repo_is_parsed_from_the_instance_id(instance_id, expected):
    assert get_org_repo(instance_id) == expected


def test_selection_keeps_only_the_language_repositories_in_order():
    rows = [
        {"instance_id": "redis__redis-10068"},
        {"instance_id": "redis__redis-py-1"},
        {"instance_id": "pydata__xarray-4629"},
        {"instance_id": "jqlang__jq-2598"},
        {},
    ]
    assert [r["instance_id"] for r in select_instances(rows, LANGUAGE_REPOS["cpp"])] == [
        "redis__redis-10068", "jqlang__jq-2598",
    ]


def test_issue_text_is_attached_and_missing_text_is_reported():
    instances = [
        {"instance_id": "a__b-1", "ground_truth": {}},
        {"instance_id": "a__b-2"},
        {"instance_id": "a__b-3"},
    ]
    attached, missing = attach_issues(instances, {"a__b-1": "bug", "a__b-3": "  "})
    assert attached == [{"instance_id": "a__b-1", "ground_truth": {}, "problem_statement": "bug"}]
    assert missing == ["a__b-2", "a__b-3"]


def test_build_fails_without_writing_when_nothing_is_selected(tmp_path):
    bench = tmp_path / "bench.jsonl"
    bench.write_text(json.dumps({"instance_id": "pydata__xarray-4629"}) + "\n", encoding="utf-8")
    output = tmp_path / "out.jsonl"
    result = CliRunner().invoke(app, [str(bench), "--language", "cpp", "-o", str(output)])
    assert result.exit_code == 1
    assert not output.exists()
