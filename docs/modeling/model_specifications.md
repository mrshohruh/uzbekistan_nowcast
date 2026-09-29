# Phase 4A — Model specifications

Mathematical definitions of every model family evaluated in Phase 4A. The
target is quarterly real GDP growth ``gdp_real_yoy_pct`` on the V1.2
verified span (2018-Q1 → 2026-Q2, 34 quarters).

Symbols:

- ``y_t`` — GDP growth in quarter ``t``.
- ``X^{(k)}_m`` — the value of predictor ``k`` in calendar month ``m``.
- ``F_t`` — the aggregated common factor for quarter ``t``.
- ``ε_t`` — model residual.

Every model is fitted anew at each expanding-window origin. No fitted
coefficient is carried across origins. No test-period observation is
used to pick a specification or to standardize a variable.

## 1. Benchmarks

### 1.1 Historical mean

`ŷ_{t | Ω_{t-1}} = (1 / n) Σ_{s < t} y_s`

where `Ω_{t-1}` is the training-window GDP series ending at quarter
``t-1``. This is the constant expanding-window mean.

### 1.2 AR(1)

`y_t = α + β_1 y_{t-1} + ε_t`

fitted by OLS on `{y_1, ..., y_{t-1}}`. The forecast is
`ŷ_{t | Ω_{t-1}} = α̂ + β̂_1 y_{t-1}`.

### 1.3 AR(2)

`y_t = α + β_1 y_{t-1} + β_2 y_{t-2} + ε_t`

fitted by OLS. Included only when the training sample has strictly more
than 3 non-missing GDP observations; otherwise the row is emitted with
``failure = 'insufficient_training_sample'``.

## 2. Bridge equations

For each candidate predictor field ``k`` and each nowcast origin
``(t, h)``:

1. Aggregate observed monthly values of ``X^{(k)}`` within quarter ``t``
   to a scalar `X̄^{(k)}_t` — arithmetic mean of the months that are
   visible at the origin under the release-lag rule.
2. Fit
   `y_t = α + β_0 y_{t-1} + β_1 X̄^{(k)}_t + ε_t`
   by OLS on the training window, dropping training quarters where any
   right-hand-side term is NaN.
3. Forecast the target quarter by evaluating the fitted regression at
   the target's `X̄^{(k)}_t` computed under the same information set.

The block bridges group predictors by economic families defined in
``src/uznowcast/models/bridge.py::ECONOMIC_BLOCKS`` and include the first
three available fields in the block; each field contributes one
additional coefficient. The parameter count for a single-field bridge is
3 (intercept, GDP lag, aggregated predictor); a three-field block bridge
has 5 parameters. The framework never fits a bridge with more parameters
than the training sample allows.

## 3. MIDAS

### 3.1 Unrestricted U-MIDAS(3)

`y_t = α + β_0 y_{t-1} + Σ_{ℓ=0}^{2} γ_ℓ X^{(k)}_{m(t, h) - ℓ} + ε_t`

where ``m(t, h)`` is the latest monthly reference period visible at
horizon ``h`` under the release-lag rule. Fitted by OLS. Parameters: 5.

### 3.2 Almon-restricted MIDAS(3, poly=1)

Same variable set but with the ``γ_ℓ`` constrained to lie on a
low-order polynomial in the lag index:

`γ_ℓ = θ_0 + θ_1 (ℓ / (L - 1))`,   ``ℓ = 0, 1, 2``,   ``L = 3``.

Substituting into the U-MIDAS equation yields four free parameters
(intercept + GDP lag + ``θ_0`` + ``θ_1``). Fitted by OLS on the
transformed design matrix (see ``_almon_basis`` in
``src/uznowcast/models/midas.py``). Parameters: 4.

## 4. Dynamic factor model (approximate)

Two-step approximate factor model in the spirit of Stock and Watson
(2002). This is **not** a full Kalman-filter DFM; the Phase 4A framework
treats it as a benchmark ragged-panel model and reports its convergence
diagnostics explicitly.

### Step 1 — Standardization

For a given tier's monthly panel ``X ∈ ℝ^{T × N}`` restricted to the
training window ``T_{\text{train}}``:

`X̃_{t,k} = (X_{t,k} - μ̂_k) / σ̂_k`

where ``μ̂_k, σ̂_k`` are the mean and (population) standard deviation of
column ``k`` computed on the non-missing entries in
``T_{\text{train}}`` only. Constant columns are protected against
divide-by-zero.

### Step 2 — EM PCA

Missing cells are imputed with the training-sample column mean and
principal components are extracted via SVD:

`X̃ = U Σ V^\top`

The top ``r`` components are held fixed and the missing cells are
updated to their PC reconstruction. The procedure repeats up to
``em_iterations = 20`` times or until the reconstruction loss changes
by less than ``em_tolerance = 1e-6``. Diagnostics
(``em_iterations``, ``reconstruction_loss``, ``fraction_missing``) are
retained in the per-fit report.

### Step 3 — Post-training projection

For each month outside the training window, the factor value is
projected onto the fixed loadings using only the observed columns of
that row:

`f_t = (L_{\text{obs}}^\top L_{\text{obs}})^{-1} L_{\text{obs}}^\top y_{\text{obs}}`

This preserves the ragged-edge property: a target-quarter month whose
columns are all missing yields a NaN factor rather than an extrapolated
value.

### Step 4 — Quarterly aggregation

`F_t = mean(f_{m₁(t)}, f_{m₂(t)}, f_{m₃(t)})`

taken over the months visible at the origin. A quarter with no visible
month for the factor yields ``NaN``.

### Step 5 — GDP regression

`y_t = α + β_0 y_{t-1} + Σ_{r=1}^{R} β_r F_{r, t} + ε_t`

fitted by OLS on the training window. R = 1 or 2 (Phase 4A only tries
``dfm_tierB_k1``, ``dfm_tierC_k1``, ``dfm_tierB_k2`` when the tier has
enough predictors).

## 5. Release-lag assumption

For a predictor with registry ``Typical publication lag (days) = L``:

- **Standard lag**: assumed released on
  ``end_of_reference_month + L``.
- **Conservative lag**: released on
  ``end_of_reference_month + max(L + 15, 3)``.

The latest usable reference month at origin ``O`` is the largest month
``m`` such that ``end_of_m + assumed_lag ≤ O``. This rule is applied
uniformly to every model above.

GDP uses a 30-day publication lag by default (see
``gdp_available_at``), which mirrors the "quarter t published around
end of first month of quarter t+1" convention.

## 6. Preprocessing safeguards

- Standardization statistics are fit on the training slice only.
- Missing values are propagated, never imputed for the modelling target.
- The robust variant (variant B) masks database observations whose
  quality flag matches
  ``extreme_log_change | nonpositive | impossible_negative``; the
  database itself is never modified.
- The June-2026 negative ``gold_exports_proxy`` flow keeps its quality
  flag and remains visible as an outlier in variant A; variant B
  removes it from the modelling frame at training time only.

## 7. Reproducibility

- Random seeds: ``random`` and ``numpy.random`` are seeded to
  ``20260929`` at CLI entry (see ``src/uznowcast/models/cli.py``).
- Every model's fit uses ``numpy.linalg.lstsq`` (deterministic).
- The EM PCA has an SVD initialization that is deterministic given the
  training-slice inputs.
- ``MODEL_LAYER_VERSION`` in ``src/uznowcast/models/__init__.py`` is
  bumped whenever a specification change would affect predictions.
