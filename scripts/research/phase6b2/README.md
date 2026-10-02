# Phase 6B.2 isolated research

Run from the repository root using the existing model environment. Additional evidence-parser dependencies are pinned in `requirements-research.txt`. The frozen model code and monthly panel remain inputs; GDP uses only qualified archived official publication events.

Offline reconstruction, evaluation and verification:

```powershell
.venv/Scripts/python.exe scripts/research/phase6b2/factors.py
.venv/Scripts/python.exe scripts/research/phase6b2/run.py
.venv/Scripts/python.exe scripts/research/phase6b2/verify.py
.venv/Scripts/python.exe -m pytest scripts/research/phase6b2/test_vintages.py -q -o addopts='' -p no:cacheprovider --basetemp results/research/phase6b2/test_tmp_new_verified > results/research/phase6b2/phase6b2_new_tests_verified.log 2>&1
.venv/Scripts/python.exe scripts/research/phase6b2/report.py
```

`run.py` initially marks tests and determinism pending. `report.py` finalizes the manifest after checking verification and test logs. Prior Phase 6B and 6B.1 tests must run in separate processes because their frozen scripts use shared bare module names. Final regression logs are retained under the isolated results directory.

`collect.py`, `discover.py` and `follow_embeds.py` collect official evidence with cached immutable raw responses, checksums and visible failures. `evidence.py` holds the reviewed publication/value ledger. New evidence requires manual verification of the publication date, GDP concept and exact source relationship before adding an event; collection alone does not establish a first release. Unknown release dates remain unknown, and suspicious chart entries are excluded from model inputs.

Results live in `results/research/phase6b2/`; the report lives in `docs/modeling/phase6b2/`. First-release and latest-master target metrics remain separate. Incomplete early release history and incomplete intervening revisions limit interpretation. No model promotion or production change is authorized by this experiment.
