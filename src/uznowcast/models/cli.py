"""python -m uznowcast.models evaluate --phase 4a."""
from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

import numpy as np

from uznowcast.models.data import load_dataset
from uznowcast.models.evaluate import evaluate, write_results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ev = sub.add_parser('evaluate', help='Run the Phase 4A evaluator')
    ev.add_argument('--phase', choices=['4a'], default='4a')
    ev.add_argument('--root', type=Path, default=Path.cwd())
    ev.add_argument('--master-dir', default='data/master')
    ev.add_argument('--registry', default='registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
    ev.add_argument('--min-train', type=int, default=8)
    ev.add_argument('--seed', type=int, default=20260929)
    ev.add_argument('--tiers', default='A,B,C',
                    help='Comma-separated tier list for bridge/MIDAS/DFM (default A,B,C).')
    ev.add_argument('--horizons', default='H1,H2,H3')
    ev.add_argument('--lag-modes', default='standard,conservative')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger('uznowcast.models')

    random.seed(args.seed)
    np.random.seed(args.seed)

    if args.command != 'evaluate':
        raise SystemExit(f'Unknown command: {args.command}')

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


if __name__ == '__main__':
    raise SystemExit(main())
