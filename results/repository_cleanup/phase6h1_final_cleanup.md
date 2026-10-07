# Phase 6H.1 final repository minimization

Status: VALIDATION_IN_PROGRESS (fresh committed-checkout proof pending).

## Protected checkpoint and scientific equivalence

Checkpoint: `fe252655d79648c8af3132f3c1d635db3bdd2253`. Its explicit selection excluded unrelated pre-existing changes. Previously missing vendored dependencies and temporary outputs were subsequently classified deliberately for this cleanup; they were not accidentally included in the checkpoint.

The old seal was reproduced first. The independent current runtime reproduces all 17 scientific artifacts byte for byte, including current nowcast, DFM structure/loadings, U-MIDAS coefficients/contributions, historical forecasts, matched metrics, news, and dashboard. Only operational code-location/checksum metadata differs.

| Output | Exact value |
|---|---:|
| DFM | 8.301152885464585 |
| U-MIDAS | 8.060649795767965 |
| 50/50 final | 8.180901340616275 |

No specification, coefficient, target convention, transformation, information rule, weight, or raw observation changed. The target remains published cumulative YTD real GDP YoY; GDP remains quarterly. The independent deterministic rerun and cached safe updater also reproduce these values. Prospective validation is still pending.

## Current seal

`config/production_seal.json` protects 81 runtime/setup/configuration files and records 63 initial replay inputs. `config/production_seal_acceptance.json` explicitly accepts the independently tested candidate. Old manifests and every candidate revision remain in Git/evidence. Text code/configuration hashes normalize CRLF to LF; scientific artifacts and immutable records preserve exact bytes through `.gitattributes`.

The seal checks active policy/specification hashes and rejects code changes. Version checks enforce master, processed, recovered-data and provenance hashes, allowing successors only through successful committed transactional manifests. Staged candidate calculations remain possible before promotion. A private corruption test verifies rejection of unexplained provenance changes.

## Consolidation and removals

Maintained Python files fell from 189 after Phase 6H to 102. The removal manifest records 34259 unique paths (34259 audit rows), covering {'F: research-only': 149, 'G: generated/staging': 31871, 'D: historical checksum/evidence-only': 2230, 'E: compatibility-only': 9}.

The phase6e compatibility namespace, historical research kernels, phase-named model/operational implementations, old shadow package, development evaluators and their tests are removed. Reusable numerical functions now live in `uznowcast.models.dfm`, `uznowcast.gdp_vintages`, `uznowcast.transforms.vintage_flows`, `uznowcast.operational.forecast`, and current operational/production modules. Content-addressed historical code objects survive solely as immutable snapshot provenance; they are neither imported nor copied as an active namespace.

Staging uses only an explicit sealed runtime/input projection, and the updater removes its staged project after validation. Historical pytest fixture trees and browser caches were inventoried individually, checked against required source evidence, and removed. Automatic review initially rejected a broad directory cleanup; the replacement was approved after exact file inventories, saved test constructors, unchanged-file guards, and 17 exact rerun-copy comparisons established its scope.

Root stale state/start documents, one-time registry builders and old logs were removed; README, operations instructions, package setup, registry/specification and batch entrypoint remain current.

## Data and provenance

All 22,609 original raw files (2,367,280,664 bytes) remain. Fresh SHA256 hashing found 4,435 duplicate groups / 6,011 extra identical copies; none were deleted. Data/bootstrap provenance contains 9,213 explicit files. The 669 already-missing historical raw references remain documented as missing; no replacement or release date was invented.

Fourteen official source-evidence files retain historical locations under `results/research/phase6b2/evidence/` because raw evidence is protected. This is a source-data exception, not historical runtime code. Their checksums and bootstrap entries preserve reproducibility. Existing immutable receipts retain their original paths and are resolved by the explicit relocation map.

## Dependency and test verification

The actual runtime trace loaded 60 repository modules. The active dependency/path scan found no historical phase imports or references to deleted phase directories. The static dead-code audit found 40 unused-import candidates, reviewed as non-runtime historical utilities/import remnants rather than evidence that numerical implementations can safely be deleted; no obsolete phase implementation remains in active code.

The test taxonomy is recorded in `phase6h1_test_inventory.csv`: CORE_DATA, TRANSFORMS, DFM, UMIDAS, COMBINATION, INFORMATION_BOUNDARY, RAGGED_EDGE, PROVENANCE, PARSERS, END_TO_END and DETERMINISM. Current DFM determinism is tested numerically; the obsolete historical determinism-file skip was removed. The full retained suite passes: **198 passed, zero failures/errors/skips**. Fresh-checkout results are finalized below after verification.

## Reproduction procedure

Install the pinned requirements and editable package as documented in README. Restore only `config/bootstrap_inputs.json` using `python -m scripts.operations.bootstrap --source-root <preserved-data-root>`. This verifies every restored file and copies no arbitrary source code or working-tree state. Then run `python -m scripts.production.run --output-dir results/diagnostics/reproduction --no-publish` and `python -X utf8 -m scripts.maintenance.validate_current`.

Fresh-checkout evidence: `phase6h1_clean_checkout_validation.json` (pending the new code commit). Full source inventories, scientific comparisons, raw duplicate groups, seal revisions, dependency scan, test XML and generated-file proofs are under `phase6h1/` and this audit directory.
