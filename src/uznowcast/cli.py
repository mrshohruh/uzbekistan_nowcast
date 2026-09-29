"""python -m uznowcast.cli {build,collect-vintage} ..."""
import argparse
import json
import logging
from pathlib import Path
from uznowcast.pipeline import build
from uznowcast.collect_vintage import collect as collect_vintage


def _configure_progress() -> logging.Logger:
    progress = logging.getLogger('uznowcast.progress')
    progress.setLevel(logging.INFO)
    progress.propagate = False
    if not progress.handlers:
        progress.addHandler(logging.StreamHandler())
    return progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('build')
    command.add_argument('--scope', choices=['pilot', 'pilot8', 'v1'], default='v1')
    command.add_argument('--root', type=Path, default=Path.cwd())
    mode = command.add_mutually_exclusive_group()
    mode.add_argument('--offline', action='store_true')
    mode.add_argument('--refresh', action='store_true')
    command.add_argument('--fx-start', help='Explicit archive start override, YYYY-MM-DD')
    command.add_argument('--fx-end', help='Explicit archive end override, YYYY-MM-DD')

    vintage = sub.add_parser(
        'collect-vintage',
        help=('Prospective vintage-collection pass. Re-fetches every '
              'registry-approved official source with refresh=True. Preserves '
              'retrieval and source-release timestamps, checksums payloads, and '
              'never overwrites older vintages.'))
    vintage.add_argument('--scope', choices=['pilot', 'pilot8', 'v1'], default='v1')
    vintage.add_argument('--root', type=Path, default=Path.cwd())

    args = parser.parse_args()
    progress = _configure_progress()
    if args.command == 'build':
        report = build(args.root, scope=args.scope, offline=args.offline, refresh=args.refresh,
                       fx_start=args.fx_start, fx_end=args.fx_end)
        summary = dict(status=report['status'], run_id=report['run_id'], failures=report['failures'],
                       validation_report=str(args.root.resolve() / 'metadata/validation_summary.json'),
                       series={key: {field: value[field] for field in ('rows', 'start', 'end', 'clean_count', 'quality_flags')}
                               for key, value in report['series'].items()})
        if 'fx_daily' in report:
            summary['fx_daily'] = {key: report['fx_daily'][key] for key in ('rows', 'start', 'end')}
        progress.info(json.dumps(summary, indent=2, default=str))
        return 1 if report['status'] == 'failed' else 0
    if args.command == 'collect-vintage':
        summary = collect_vintage(args.root, scope=args.scope)
        progress.info(json.dumps(summary, indent=2, default=str))
        return 1 if summary['status'] == 'failed' else 0
    raise SystemExit(f'Unknown command: {args.command}')


if __name__ == '__main__':
    raise SystemExit(main())
