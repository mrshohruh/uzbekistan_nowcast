# Phase 6B.1 isolated GDP-boundary repair

No network calls, data collection, production edits or Phase 6B overwrites.
Use the existing Phase 6B pinned environment. All new writes stay here and in
the Phase 6B.1 results/docs directories. The persistent protected-before
inventory must not be overwritten to bypass a mismatch.

The initial reproduction was executed before the repaired boundary existed:

```powershell
.venv/Scripts/python.exe scripts/research/phase6b1/reproduce.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts='' scripts/research/phase6b1/test_reproduction.py
```

Reproduce the corrected experiment, tests and finalized manifest:

```powershell
.venv/Scripts/python.exe scripts/research/phase6b1/run.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts='' scripts/research/phase6b1 --junitxml=results/research/phase6b1/phase6b1_test_results.xml
.venv/Scripts/python.exe scripts/research/phase6b1/finalize.py
```

The immutable Phase 6B state-space core is imported, not copied or altered.
Only primary domestic factors are re-estimated; every factor path is checked
against its original. GDP timing is quarter-end + 46 days, the existing
registry 31-day lag plus Phase 5A conservative 15-day rule, used for both
monthly lag experiments. Actual per-quarter release dates remain null; the
fallback availability date is explicitly an assumption. Unknown availability
is rejected. Missing target-lag GDP makes Bridge B and its combination
unavailable, without substitution. Frozen historical benchmarks are audited
over their entire saved sample and rerun separately with the same GDP gate.

The finalizer checks test XML, saved training gates and source/protected
checksums, records numeric rerun identity and appends verification evidence.
