"""Run ingestion/collection tests in short, private Windows workspaces."""
from pathlib import Path
import sys
import uuid

import pytest
from _pytest.tmpdir import TempPathFactory

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True


def main():
    temporary = ROOT / '.tmp' / ('a2_' + uuid.uuid4().hex[:6])
    temporary.mkdir(parents=True)
    # pytest's restrictive chmod on basetemp is incompatible with this managed
    # Windows workspace. Ordinary private directories retain the workspace ACL.
    def base(factory):
        factory._basetemp = temporary
        return temporary
    def mktemp(factory, basename, numbered=True):
        path = temporary / ('t_' + uuid.uuid4().hex[:7])
        path.mkdir()
        return path
    TempPathFactory.getbasetemp = base
    TempPathFactory.mktemp = mktemp
    paths = sys.argv[1:] or ['tests/collection']
    report = ROOT / 'results/phase8a2/validation' / ('tests_' + uuid.uuid4().hex[:8] + '.xml')
    report.parent.mkdir(parents=True, exist_ok=True)
    print('Isolated workspace:', temporary)
    print('JUnit report:', report)
    return int(pytest.main([*paths, '-p', 'no:cacheprovider', '-q', '-o', 'addopts=',
                           '--junitxml', str(report)]))


if __name__ == '__main__':
    sys.exit(main())
