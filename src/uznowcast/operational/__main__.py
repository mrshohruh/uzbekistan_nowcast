"""Command-line entry point for the Phase 5A operational nowcast."""

from __future__ import annotations

import argparse
from pathlib import Path

from uznowcast.operational.phase5a import run_phase5a


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 5A GDP nowcast")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--as-of-date", default="2026-09-30")
    args = parser.parse_args()
    result = run_phase5a(args.root, as_of_date=args.as_of_date)
    headline = result["nowcasts"].loc[
        result["nowcasts"]["production_headline_flag"], "prediction"
    ].iloc[0]
    print(
        f"Phase 5A: {result['target']['target_quarter']} "
        f"{result['target']['horizon']} ensemble={headline:.6f}%"
    )


if __name__ == "__main__":
    main()
