# Phase 2C.1 results — Rosstat `russia_ipi` TLS resolution attempt

Phase 2C completed with 28 of 29 V1 series automated; the sole unresolved series was `russia_ipi`.
Phase 2C.1 tried to resolve it under the constraint that TLS verification must not be disabled or
weakened, and that the provider (Rosstat) must not be substituted. The attempt did not succeed:
the outcome remains `russia_ipi = unresolved`, but a supported, secure opt-in path has been added
so the operator can complete it after making an explicit policy decision.

---

## Step 1 — TLS diagnosis (Rosstat's own PKI)

Reproducible probe from this environment on 2026-09-29:

| Field | Value |
| --- | --- |
| OS | Windows 10 Pro 10.0.19045 |
| Python | 3.12.10 (MSVC v.1943, AMD64) |
| requests | 2.34.2 |
| urllib3 | 2.8.0 |
| OpenSSL (Python) | 3.0.16 |
| certifi | 2026.07.22 (`.venv/Lib/site-packages/certifi/cacert.pem`) |
| Requested host | `rosstat.gov.ru` (registry-approved Rosstat host) |
| Redirect chain | none — the failure occurs during the TLS handshake, before HTTP |

`ssl.create_default_context()` (certifi) fails with:

```
SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
  certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)
```

The peer leaf certificate presented by `rosstat.gov.ru` (captured via an unverified
handshake purely to read the chain) is:

```
Subject:  CN=*.rosstat.gov.ru, O="Федеральная служба государственной статистики",
          serialNumber=1047708023483, INN=7708234640, C=RU, ...
Issuer:   CN="Russian Trusted Sub CA",
          O="The Ministry of Digital Development and Communications", C=RU
Not before: 2025-12-08
Not after:  2026-12-08
AIA:      http://nuc-cdp.voskhod.ru/cdp/subca_ssl_rsa2024.crt
          http://nuc-cdp.digital.gov.ru/cdp/subca_ssl_rsa2024.crt
CRL:      http://nuc-cdp.voskhod.ru/cdp/subca_ssl_rsa2024_ov.crl
```

The chain terminates at the **Russian Trusted Root CA**, issued by the Russian Federation's
Ministry of Digital Development. This root is not present in Mozilla NSS, certifi, nor
common OS trust stores outside Russia.

The AIA URLs are reachable over plain HTTP:

```
GET http://nuc-cdp.voskhod.ru/cdp/subca_ssl_rsa2024.crt → 200 (2455 bytes)
GET http://nuc-cdp.digital.gov.ru/cdp/subca_ssl_rsa2024.crt → 200 (2455 bytes)
```

but that only exposes the sub-CA. The Russian Trusted Root itself is only signed by the
Russian government's PKI.

## Step 2 — OS system-trust probe

`truststore` (0.10.4) was installed and `truststore.inject_into_ssl()` was called so that
Python's TLS goes through the Windows certificate store instead of certifi. The Windows ROOT
store on this host was enumerated with `ssl.enum_certificates('ROOT')`:

- Total ROOT certificates: 46
- Certificates matching `Russian Trusted` or `Ministry of Digital`: **0**

Handshake result under system trust:

```
SSLCertVerificationError:
  A certificate chain processed, but terminated in a root certificate
  which is not trusted by the trust provider.
```

This is the correct behaviour of a well-configured OS: the Russian Trusted Root is a
sovereign CA whose acceptance is a policy decision, not a code decision.

## Step 3 — Other official Rosstat delivery paths

To stay within the "official Rosstat provider" constraint, alternative Rosstat-operated
hosts and paths were probed on the same day.

| Host | Reachable | TLS chain | Notes |
| --- | --- | --- | --- |
| `rosstat.gov.ru`, `www.rosstat.gov.ru` | yes | Russian Trusted Sub CA (fails) | primary registry host |
| `showdata.gks.ru` | yes | Russian Trusted CA family (fails) | legacy Rosstat data host |
| `www.gks.ru`, `gks.ru` | yes | Russian Trusted CA family (fails) | legacy Rosstat host |
| `fedstat.ru`, `www.fedstat.ru` | yes | **Let's Encrypt (verifies cleanly)** | official Rosstat/EMISS delivery, but the site **geo-blocks non-RU IPs — returns HTTP 403 "Forbidden"** for requests from this environment |
| `opendata.rosstat.gov.ru`, `data.rosstat.gov.ru`, `sdmx.rosstat.gov.ru`, `api.rosstat.gov.ru`, `static.rosstat.gov.ru` | DNS `NXDOMAIN` | — | no such subdomains |
| `sophist.hse.ru` | connect timeout | — | HSE aggregate, not Rosstat-operated anyway |

`fedstat.ru` was the only official Rosstat delivery path with a Western-trusted TLS chain,
and its geo-block makes it useless from outside Russia even though its cert is valid. No
non-Rosstat provider was substituted, per the AGENTS.md contract.

## Step 4 — Implementation

Because the only feasible path to verified TLS goes through the operator installing
Russia's Trusted Root CA into the OS trust store — a sovereign policy decision that
must not be silently taken by pipeline code — no automated ingestion was implemented for
`russia_ipi`. Instead, the secure opt-in scaffolding recommended by the spec was added
so the operator can complete ingestion once (and if) they accept that trust.

Added to [src/uznowcast/io/http.py](src/uznowcast/io/http.py):

```python
def _install_system_trust():
    if os.environ.get('UZNOWCAST_USE_SYSTEM_TRUST') != '1':
        return False
    import truststore
    truststore.inject_into_ssl()
    return True
```

Semantics:

- `UZNOWCAST_USE_SYSTEM_TRUST` unset (default) → certifi bundle, unchanged behavior for the
  28 automated series. `russia_ipi` continues to fail with a real
  `SSLCertVerificationError`, no observations are produced, no payloads are written.
- `UZNOWCAST_USE_SYSTEM_TRUST=1` → `ssl.create_default_context()` uses the Windows/macOS/Linux
  OS trust store via `truststore`. TLS verification stays **on**; the only thing the operator
  changes is _which set of roots_ is trusted. If they have installed the Russian Trusted
  Root into their OS store, the Rosstat handshake succeeds and the existing downloader/parser
  path completes. If they have not, verification still fails, cleanly, with a real error.
- Ignored when `--offline` is used, because no live TLS handshake takes place.

Provenance, retry, cache, checksum, and archive semantics are unchanged; only the CA source
is switched. `requests.get(..., verify=False)` is never called. `verify=` is never set to
`False`. `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` are never mutated.

## Step 5 — Historical consistency

Not yet applicable: no `russia_ipi` observations have been retrieved. Once the operator
opts in (or a Rosstat delivery path with a Western-trusted cert becomes reachable), the
existing `download_rosstat_page` + parser skeleton must (a) identify the exact national
IPI dataset (Rosstat's "Индекс промышленного производства"), (b) archive the source file
immutably, (c) preserve the raw index convention (previous-year=100 vs. 2018=100), and
(d) surface Rosstat's periodic base-year rebasings as a structural break rather than
silently splicing series.

## Step 6 — Tests

Four new offline unit tests were added to
[tests/test_http.py](tests/test_http.py) covering the opt-in flag:

- `test_system_trust_off_by_default` — no env var, no `truststore` call, default flag `False`.
- `test_system_trust_opt_in_calls_truststore` — env var set, `truststore.inject_into_ssl()`
  is invoked exactly once.
- `test_system_trust_ignored_in_offline_mode` — `offline=True` never touches TLS state.
- `test_system_trust_missing_package_raises` — a clear `RuntimeError` when the operator
  turns the flag on without installing the package (no silent fallback).

Live-network tests are still forbidden. Total suite: **74 tests, all passing** (up from 70
at end of Phase 2C).

## Step 7 — Rebuild V1

Rebuilt with `python -m uznowcast.cli build --scope v1 --offline` after the code changes.

- Build status: `partial_with_failures` (unchanged; correct outcome per Step 8).
- Automated: 28 of 29 V1 series.
- Unresolved: `russia_ipi` — `Offline cache missing: https://rosstat.gov.ru/enterprise_industrial`.
- `v1_monthly.parquet` / `.xlsx`: 801 rows × 29 columns (unchanged).
- `v1_observations_long.parquet`: 6 739 rows × 20 columns (unchanged).
- `gdp_quarterly.parquet` / `.xlsx`: 34 rows (unchanged).
- Raw payloads under `data/raw/` are unchanged during replay (offline mode never writes).
- No duplicate vintages introduced (checked via `metadata/vintages.parquet`).
- Panel remains ragged. No imputation, no interpolation. GDP remains quarterly.

## Step 8 — Rationale for keeping `russia_ipi` unresolved

Exact technical reason: `rosstat.gov.ru` presents a leaf certificate signed by
`CN=Russian Trusted Sub CA, O=The Ministry of Digital Development and Communications`,
whose root is not in certifi, Mozilla NSS, or this host's Windows OS store. Every attempted
path to verified TLS requires adding the Russian Trusted Root as a trusted CA on the
operator's machine. That is a sovereign trust decision, not something pipeline code should
take silently on the operator's behalf. Once made, the added `UZNOWCAST_USE_SYSTEM_TRUST=1`
opt-in path completes ingestion without any further code change.

Bypassing TLS (`verify=False`, `CERT_NONE`, ignoring hostname/chain validation, injecting
a self-hosted "trusted" bundle without operator consent, monkey-patching `ssl` at import
time) is rejected because it would (a) silently accept any certificate for `rosstat.gov.ru`
without any assurance the responder is Rosstat, (b) contradict the explicit Step 8 rule of
this task, and (c) contradict the AGENTS.md contract that provenance and source authenticity
must be visibly preserved.

Endpoints tested and their outcomes are recorded in Step 3 above.

## Recommendations added to registry documentation

[docs/phase2c_registry_recommendations.md](docs/phase2c_registry_recommendations.md)
already carried a `russia_ipi` recommendation. It is now supplemented (see the auto-generated
table maintained by `src/uznowcast/reporting.py`) with the observation that `fedstat.ru` is
the only Rosstat-operated host with a Western-trusted cert and that its geo-block makes it
inoperable from this environment.

## What the operator can do

Two options, both explicit:

1. **Install the Russian Trusted Root CA** into their OS trust store (Windows: import into
   `Trusted Root Certification Authorities`; Linux: add to `/usr/local/share/ca-certificates/`
   and run `update-ca-certificates`), then set `UZNOWCAST_USE_SYSTEM_TRUST=1` and re-run
   `python -m uznowcast.cli build --scope v1`. TLS verification stays enabled; the leaf
   certificate now validates against the operator-supplied root, and `russia_ipi` ingests
   through the normal pipeline.
2. **Run the pipeline from within a network that can reach `fedstat.ru`** (i.e. from Russia,
   or through a Russia-based network path), and register a new `fedstat.ru` machine URL as
   a Phase 2C.2 registry amendment. The provider stays Rosstat.

Neither is done automatically. Both are recorded here so the reproducibility contract holds.

## No forecasting model

Per the standing constraint, no forecasting or nowcasting model was built. Phase 2C.1 is
strictly a TLS-resolution attempt for the last V1 series, and it stops here.
