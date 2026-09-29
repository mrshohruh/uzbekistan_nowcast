"""python -m uznowcast.models evaluate --phase {4a,4a1}."""
from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

import numpy as np

from uznowcast.models.data import load_dataset
from uznowcast.models.evaluate import evaluate, write_results
from uznowcast.models.evaluate_v11 import run_phase_4a1, write_phase_4a1_results


def _run_phase_4a(args, logger) -> int:
    dataset = load_dataset(args.root, master_dir=args.master_dir,
                            registry_relative=args.registry)
    results = evaluate(
        dataset,
        horizons=tuple(h.strip() for h in args.horizons.split(',') if h.strip()),
        lag_modes=tuple(m.strip() for m in args.lag_modes.split(',') if m.strip()),
        min_train=args.min_train,
        tiers=tuple(t.strip() for t in args.tiers.split(',') if t.strip()),
    )
    counts = write_results(args.root, results)
    logger.info(json.dumps(dict(status='written', **counts,
                                first_evaluation_quarter=results['first_evaluation_quarter'],
                                last_evaluation_quarter=results['last_evaluation_quarter'],
                                min_train=results['min_train']),
                            indent=2, default=str))
    return 0


def _run_phase_4a1(args, logger) -> int:
    results = run_phase_4a1(
        args.root,
        master_dir=args.master_dir,
        registry_relative=args.registry,
        strict_tiers=not args.allow_missing,
        allow_fixture_dir=False,
        horizons=tuple(h.strip() for h in args.horizons.split(',') if h.strip()),
        lag_modes=tuple(m.strip() for m in args.lag_modes.split(',') if m.strip()),
        include_small_sample=not args.no_small_sample,
    )
    counts = write_phase_4a1_results(args.root, results)
    logger.info(json.dumps(dict(status='written', **counts,
                                first_evaluation_quarter=results['first_evaluation_quarter'],
                                last_evaluation_quarter=results['last_evaluation_quarter'],
                                monthly_sha256=results['fingerprint'].monthly_sha256,
                                quarterly_sha256=results['fingerprint'].quarterly_sha256,
                                registry_sha256=results['fingerprint'].registry_sha256,
                                holdout_quarters=list(results['frozen'].holdout_quarters)),
                            indent=2, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ev = sub.add_parser('evaluate', help='Run the Phase 4A / 4A.1 evaluator')
    ev.add_argument('--phase', choices=['4a', '4a1'], default='4a1',
                    help="'4a' is the original fixture-permissive framework; "
                         "'4a1' is the production evaluator that refuses the "
                         "fixture rehearsal directory and enforces matched-quarter "
                         "comparisons and effective-training safeguards.")
    ev.add_argument('--root', type=Path, default=Path.cwd())
    ev.add_argument('--master-dir', default='data/master')
    ev.add_argument('--registry', default='registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
    ev.add_argument('--min-train', type=int, default=8,
                    help='Phase 4A only. Phase 4A.1 uses the effective-training '
                         'safeguard instead.')
    ev.add_argument('--seed', type=int, default=20260929)
    ev.add_argument('--tiers', default='A,B,C',
                    help='Comma-separated tier list for bridge/MIDAS/DFM (default A,B,C).')
    ev.add_argument('--horizons', default='H1,H2,H3')
    ev.add_argument('--lag-modes', default='standard,conservative')
    ev.add_argument('--allow-missing', action='store_true',
                    help='Phase 4A.1 only. Warn on missing Tier A/B/C predictors '
                         'instead of failing.')
    ev.add_argument('--no-small-sample', action='store_true',
                    help='Phase 4A.1 only. Skip the small-sample sensitivity run.')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger('uznowcast.models')

    random.seed(args.seed)
    np.random.seed(args.seed)

    if args.command != 'evaluate':
        raise SystemExit(f'Unknown command: {args.command}')

    if args.phase == '4a':
        return _run_phase_4a(args, logger)
    if args.phase == '4a1':
        return _run_phase_4a1(args, logger)
    raise SystemExit(f'Unknown phase: {args.phase}')


if __name__ == '__main__':
    raise SystemExit(main())
