# Official POS regression fixtures

These are checksum-identical copies of existing official CBU receipts, frozen for offline parser regression. `pos_receipts.json` preserves the original source URL, HTTP status, retrieval/update timestamps, SHA-256 and archive reference.

- `pos_apreily_page.html`: official payment-system article992617, archived2026-10-05. It spells April as `Apreily` and January as `Yanuary` and links the XLSX attachment.
- `pos_apreily.xlsx`: the corresponding official workbook. Its English sheet specifies the as-of date April1,2023, January–March reporting range and amount in mln.sum. Exact Total:52,919,100.966056414 million UZS.

Page and attachment evidence are distinct. Fixtures do not authorize any extension of POS production comparability beyond December2024. Synthetic mutations in tests are confined to memory/isolated workspaces and are never observations in the production database.
