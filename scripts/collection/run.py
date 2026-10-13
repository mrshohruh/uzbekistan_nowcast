"""Supported collection-only CLI. Never imports or invokes forecast builders."""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

from scripts.collection.engine import collect
from scripts.collection.versions import recover
from scripts.operations.state import operational_lock


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--commit', action='store_true', help='Commit a collection version; never production files')
    mode.add_argument('--dry-run', action='store_true', help='Validate isolated candidates (default)')
    mode.add_argument('--check-only', action='store_true', help='Same isolated validation without publication')
    p.add_argument('--offline', action='store_true', help='Replay archived receipts; sources LIVE_NOT_TESTED')
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--store', type=Path, help='Collection evidence/version store; default data/collection')
    p.add_argument('--as-of', help='Historical observed cutoff; requires --offline')
    p.add_argument('--recover-run', help='Explicitly reconcile an interrupted collection journal under writer lock')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.recover_run:
            with operational_lock(args.root):
                status = recover(args.store or args.root / 'data/collection', args.recover_run)
            print(json.dumps(dict(status=status, forecast_execution=False)))
            return 0
        result = collect(args.root, store=args.store, commit=args.commit,
                         offline=args.offline, asof=args.as_of)
        print(json.dumps(result, indent=2, default=str))
        return result['exit_code']
    except Exception as error:
        print(json.dumps(dict(status='COLLECTION_BLOCKED', error_type=type(error).__name__,
                              error=str(error), forecasts_calculated=False)), file=sys.stderr)
        return 4


if __name__ == '__main__':
    sys.exit(main())
