# Phase 6G — fixed-weight M2 ensemble validation

This research phase changes no production settings or dashboard and reads no FDI data.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m scripts.phase6g.run
.venv/Scripts/python.exe -m scripts.phase6g.verify
.venv/Scripts/python.exe -m scripts.phase6g.tests existing
.venv/Scripts/python.exe -m scripts.phase6g.tests new
.venv/Scripts/python.exe -m scripts.phase6g.finalize
```

Use the pinned project dependencies plus `scripts/phase6f/requirements-research.txt`.

The reproduction gate refits the frozen Phase 6E DFM/U-MIDAS/ensemble and Phase 6F M2-L1/L2 at all twelve holdout origins and the exact archived current cutoff. A mismatch stops promotion testing. Earlier targets are drawn from the verified GDP first-release registry; unavailable or unstable models are excluded with explicit reasons. The same seven models and identical origins form the strict-common sample.

Historical M2 and other predictor values remain revised snapshots. Publication masks address reference-period timing, and verified archived GDP publications determine GDP information sets. This is availability-aware pseudo-real-time; historical predictor revision-value leakage is unresolved. Earlier development origins are retrospective robustness evidence, not independent holdout observations.

H1 is the first target-quarter month, H2 the second, H3 the third. The requested reverse revision view is also supplied. Fixed-weight sensitivities compare both with production 50/50 and with the unchanged DFM at each identical weight. The main challenger stays G2 50/50. Quarter-cluster bootstrap diagnostics do not imply independent horizon observations or resolve historical-value-vintage limitations.

Only `results/phase6g/` receives generated artifacts. `verify` refits the complete experiment twice; numerical CSV checksums must match. The test runner avoids Windows private temporary-directory ACL issues by creating temporary directories under the Phase 6G output folder with inherited permissions.
