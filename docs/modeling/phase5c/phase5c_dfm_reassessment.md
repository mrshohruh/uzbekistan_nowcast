# Phase 5C DFM reassessment

Phase 4B retained no DFM (`selected_dfm=None`). Its approximate
factor variants failed the accuracy gate and remained diagnostic. Phase 5C therefore did
not relabel the old model: it tested only one-factor, tight-panel variants based on screened
signals, with the same real-time masking and expanding windows. See
`phase5c_dfm_metrics.csv` and `phase5c_dfm_diagnostics.csv`. No DFM is production eligible.

The frozen Phase 4B comparison points were:

- `dfm_tierA_k1`: worst H3 relative RMSE vs AR(2) 1.480; qualified=False
- `dfm_tierB_k1`: worst H3 relative RMSE vs AR(2) 1.335; qualified=False
- `dfm_tierC_k1`: worst H3 relative RMSE vs AR(2) 1.421; qualified=False
