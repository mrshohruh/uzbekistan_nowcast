# POS diagnosis

Original run: 46 failed articles and 14 missing months. Main failure classes:

| Failure | Articles |
|---|---:|
| Reporting date not recognized | 16 |
| Official attachment HTTP 404 | 9 |
| Exact amount header not matched | 8 |
| No unique supported unit-verified extraction | 4 |
| Avgust spelling | 2 |
| Truncated Total row (previous IndexError) | 2 |
| Missing source file | 1 |
| Ambiguous numeric amount | 1 |
| Page as-of/range disagreement | 1 |
| Workbook/page period disagreement | 1 |
| Insecure HTTP attachment rejected | 1 |

These are heterogeneous archive availability, layout/format, date consistency and parser-compatibility failures. Header mismatch does not establish a safe alternative selector. An ambiguous amount is not repaired by guessing separators. HTTP-only references are not fetched through a policy bypass. Dates/layouts beyond the verified correction remain unsupported.

Small verified fix: normalize whole-word Avgust to August. Articles 1222302 and 1843091 explicitly state January–July 2023/2024. The first workbook spells August conventionally; the second spells Avgust but independently states January–July. Both have the exact amount header, explicit million-sum unit and unique numeric Total. Results: July 2023 YTD 135,634,744.5458963 and July 2024 YTD 181,894,359.7136975 million UZS. Original workbook bytes and SHA256 evidence are frozen in tests/fixtures/collection/avgust. Contradictory reporting ranges still fail.

A second defensive correction replaces IndexError for a shortened Total row with explicit `POS Total row lacks the amount column`. It does not recover or admit those observations.

Checksum-verified full archive replay now yields **44 failed articles and 12 missing months**. Restored months are 2023-07 and 2024-07. Remaining gaps: 2020-07, 2020-10, 2021-02, 2021-07, 2021-10, 2022-03, 2022-04, 2022-09, 2023-05, 2023-06, 2024-06, 2024-11. These are internal gaps between parsed endpoints; they do not describe complete registry coverage before June 2020 or after September 2025.

POS still fails admission: June 2022 candidate log growth 51.78182046890676 versus accepted 51.781824018077316, and January 2023 candidate 52.42464600958563 exceed the unchanged 50-point rule. The small June revision does not authorize a tolerance override. Source degradation remains explicit. All post-2024 candidates remain ineligible; the production cap stays December 2024. Missing-period, source-error and extreme-growth flags are preserved. No production observations were written.
