"""Group-clustered bootstrap behavior and evaluator integration."""

from __future__ import annotations

import pytest

from finmirror.uncertainty import clustered_bootstrap


def test_clustered_bootstrap_is_deterministic() -> None:
    grouped = {
        "accuracy": {
            "a": [1.0, 1.0],
            "b": [0.0, 0.0],
            "c": [1.0, 0.0],
        }
    }
    left = clustered_bootstrap(grouped, replicates=500, seed=7)
    right = clustered_bootstrap(grouped, replicates=500, seed=7)
    assert left == right
    interval = left["intervals"]["accuracy"]
    assert interval["estimate"] == pytest.approx(0.5)
    assert 0.0 <= interval["lower"] <= interval["estimate"]
    assert interval["estimate"] <= interval["upper"] <= 1.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"replicates": 99}, "at least 100"),
        ({"confidence": 1.0}, "between 0 and 1"),
    ],
)
def test_bootstrap_rejects_invalid_configuration(kwargs, match) -> None:
    with pytest.raises(ValueError, match=match):
        clustered_bootstrap({"x": {"a": [1.0]}}, **kwargs)


def test_bootstrap_rejects_mismatched_clusters() -> None:
    with pytest.raises(ValueError, match="cluster IDs"):
        clustered_bootstrap(
            {"left": {"a": [1.0]}, "right": {"b": [1.0]}},
            replicates=100,
        )


def test_evaluator_reports_group_intervals(oracle_report, memorized_report) -> None:
    oracle = oracle_report["uncertainty"]
    assert oracle["method"] == "group-clustered percentile bootstrap"
    assert oracle["cluster"] == "pair_group_id"
    assert oracle["cluster_count"] == 18
    assert oracle["replicates"] == 2000
    for interval in oracle["intervals"].values():
        assert interval == {"estimate": 1.0, "lower": 1.0, "upper": 1.0}

    memorized = memorized_report["uncertainty"]["intervals"]
    assert memorized["case_accuracy"]["lower"] <= 5 / 7
    assert memorized["case_accuracy"]["upper"] >= 5 / 7
    assert memorized["pair_reliability"]["upper"] == 0.0
