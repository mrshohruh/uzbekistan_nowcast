# Phase 8A.3B results

Partial resolution. Reserves September admission is behaving as specified: the exact official level produces -54.02293220066543 YoY log growth, beyond the existing 50-point threshold. No demonstrated technical reserves defect was found or changed. September remains withheld pending explicit source/economic review.

Fixed the independently corroborated POS Avgust spelling and made truncated Total-row errors explicit. Archived replay reduces failed articles **46 → 44** and missing internal months **14 → 12**. POS remains degraded and inadmissible because of remaining archive failures and extreme historical candidates. Its December 2024 eligibility cap is unchanged.

The supplied Windows run's live receipts support actual downloads and parsing for all nine source families. This phase used those existing immutable receipts for offline replay; it performed no new live verification and did not bypass the restricted network environment.

Broad regression: **60 passed, zero failed**. Focused regression: **5 passed, zero failed**, including independent gold acceptance while reserves and POS fail. This represents **61 distinct passing tests** because four focused cases overlap. XML evidence is in validation/. Failed sources retain their prior accepted observations; degradation is visible and does not block independent validated indicators.

Modified runtime file: `scripts/collection/pos.py` only. Added `tests/collection/test_phase8a3b.py`, four Avgust fixture/evidence files, these four reports and validation artifacts. Successful industrial/PPI/FX/gold/M2/GDP adapters, transformations, GDP first-release rules and scientific thresholds are unchanged.

Production freeze PASS: all 1,961 original baseline files unchanged, 81 accepted runtime hashes and current-version integrity pass; forecast stays **8.180901340616275%**, with 0.5/0.5 weights. No production data or collection version committed, scheduler installed, model changed or GDP forecast recalculated.

Next Windows CMD command from the repository root:

```bat
run_collection.bat --dry-run
```

Exit 2 remains expected while reserves/POS admission or archive limitations persist. Inspect source_status.csv, observation_decisions.csv, validation_reports.json and archive_audit.csv in the new run; restored POS parsing does not imply restored admission.
