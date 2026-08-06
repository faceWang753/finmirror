#!/usr/bin/env python3
"""Build the blinded Statistics Canada pilot review data for GitHub Pages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finmirror.models import BenchmarkCase
from finmirror.review import load_expert_review_status
from finmirror.review_app import write_review_data


def _read_cases(pilot_root: Path) -> list[BenchmarkCase]:
    rows = []
    for name in ("reference.jsonl", "counterfactuals.jsonl"):
        with (pilot_root / name).open("r", encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return [BenchmarkCase.from_dict(row) for row in rows]


def build(pilot_root: Path, output_path: Path) -> None:
    status = load_expert_review_status(pilot_root / "review-status.json")
    write_review_data(_read_cases(pilot_root), status, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilot",
        type=Path,
        default=Path("sources/v0.2/calibration/statcan-gdp-2025q2-q3"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/demo/review/data.js"),
    )
    args = parser.parse_args()
    build(args.pilot, args.out)
    print(f"Wrote blinded review data to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
