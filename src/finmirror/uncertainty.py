"""Dependency-free, group-clustered bootstrap confidence intervals."""

from __future__ import annotations

import random
import statistics
from typing import Any


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot take a percentile of an empty vector")
    position = probability * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def clustered_bootstrap(
    grouped_metrics: dict[str, dict[str, list[float]]],
    *,
    replicates: int = 2000,
    seed: int = 1729,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Percentile intervals that resample complete paired-case groups.

    Values inside a sampled cluster are kept together. The routine is deterministic
    for a fixed seed and is intended for descriptive benchmark uncertainty, not a
    substitute for a pre-registered statistical design.
    """

    if replicates < 100:
        raise ValueError("Bootstrap requires at least 100 replicates")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if not grouped_metrics:
        raise ValueError("No grouped metrics supplied")

    metric_names = sorted(grouped_metrics)
    cluster_ids = sorted(next(iter(grouped_metrics.values())))
    if not cluster_ids:
        raise ValueError("No clusters supplied")
    expected_clusters = set(cluster_ids)
    for metric, clusters in grouped_metrics.items():
        if set(clusters) != expected_clusters:
            raise ValueError(f"{metric}: cluster IDs do not match")
        if any(not values for values in clusters.values()):
            raise ValueError(f"{metric}: empty cluster")

    estimates = {
        metric: statistics.fmean(
            value for cluster_id in cluster_ids for value in grouped_metrics[metric][cluster_id]
        )
        for metric in metric_names
    }
    draws: dict[str, list[float]] = {metric: [] for metric in metric_names}
    generator = random.Random(seed)
    for _ in range(replicates):
        sampled = generator.choices(cluster_ids, k=len(cluster_ids))
        for metric in metric_names:
            values = [
                value for cluster_id in sampled for value in grouped_metrics[metric][cluster_id]
            ]
            draws[metric].append(statistics.fmean(values))

    alpha = (1.0 - confidence) / 2
    intervals = {}
    for metric in metric_names:
        ordered = sorted(draws[metric])
        intervals[metric] = {
            "estimate": estimates[metric],
            "lower": _percentile(ordered, alpha),
            "upper": _percentile(ordered, 1.0 - alpha),
        }
    return {
        "method": "group-clustered percentile bootstrap",
        "cluster": "pair_group_id",
        "confidence": confidence,
        "replicates": replicates,
        "seed": seed,
        "cluster_count": len(cluster_ids),
        "intervals": intervals,
    }
