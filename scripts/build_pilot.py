"""Compatibility wrapper for the single pilot entry point."""
from uznowcast.cli import main
import sys

if __name__ == '__main__':
    sys.argv[1:1] = ['build', '--scope', 'pilot']
    raise SystemExit(main())
