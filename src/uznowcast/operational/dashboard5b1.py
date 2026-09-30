"""Phase 5B.1 hardened management dashboard.

Same visual language as the Phase 5B dashboard, plus:
  - horizon selector defaults to the current operational stage;
  - publication-readiness panel;
  - model-specific data-quality flags (distinct from system warnings);
  - reworded empirical error range (not a confidence interval).
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from uznowcast.operational.dashboard import (
    LABELS, _actual_vs_nowcast, _comparison_bars,
)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], *, limit: int | None = None) -> str:
    view = frame.head(limit) if limit else frame
    head = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
    rows = []
    for item in view.to_dict(orient="records"):
        cells = []
        for key, _ in columns:
            value = item.get(key)
            if isinstance(value, float):
                text = "—" if pd.isna(value) else f"{value:.3f}"
            elif value is None or (isinstance(value, float) and pd.isna(value)):
                text = "—"
            else:
                text = str(value)
            cells.append(f"<td>{escape(text)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-scroll"><table><thead><tr>'
        + head + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div>"
    )


def _validation_tables(predictions: pd.DataFrame, metrics: pd.DataFrame,
                       default_horizon: str) -> str:
    """Panels for H1, H2, H3 — default panel matches the operational stage."""
    pieces = []
    for horizon in ("H1", "H2", "H3"):
        block = predictions.loc[
            (predictions["horizon"] == horizon)
            & (predictions["lag_mode"] == "standard")
        ]
        pivot = block.pivot(index="target_quarter", columns="model", values="prediction")
        actual = block.drop_duplicates("target_quarter").set_index("target_quarter")["actual"]
        rows = []
        for quarter in pivot.index:
            cells = [f"<td>{escape(str(quarter))}</td>", f"<td>{actual.loc[quarter]:.1f}</td>"]
            for model in ("ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"):
                cells.append(f"<td>{float(pivot.loc[quarter, model]):.2f}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        pieces.append(
            f'<div class="validation-panel" data-horizon="{horizon}" '
            f'style="display:{"block" if horizon == default_horizon else "none"}">'
            '<div class="table-scroll"><table><thead><tr><th>Quarter</th><th>Actual</th>'
            '<th>AR(1)</th><th>AR(2)</th><th>U-MIDAS</th><th>Ensemble</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div></div>"
        )
    metric_rows = []
    order = ("ensemble_ar2_umidas_usd", "umidas_usd_uzs_mom_dlog", "ar1", "ar2")
    for model in order:
        values = []
        for horizon in ("H1", "H2", "H3", "POOLED_H1_H3"):
            match = metrics.loc[
                (metrics["model"] == model)
                & (metrics["horizon"] == horizon)
                & (metrics["lag_mode"] == "standard")
            ]
            values.append(float(match.iloc[0]["rmse"]))
        cls = ' class="highlight-row"' if model == "ensemble_ar2_umidas_usd" else ""
        metric_rows.append(
            f"<tr{cls}><td>{escape(LABELS[model])}</td>"
            + "".join(f"<td>{v:.3f}</td>" for v in values) + "</tr>"
        )
    options = "".join(
        f'<option value="{h}"{" selected" if h == default_horizon else ""}>{h}</option>'
        for h in ("H1", "H2", "H3")
    )
    return (
        '<div class="validation-control"><label for="horizon-select">'
        f"Quarter table horizon (default = current operational stage {escape(default_horizon)})"
        "</label>"
        f'<select id="horizon-select">{options}</select></div>'
        + "".join(pieces)
        + '<h3 class="subhead">RMSE by horizon</h3><div class="table-scroll"><table><thead><tr>'
        '<th>Frozen model</th><th>H1</th><th>H2</th><th>H3</th><th>Pooled H1–H3</th>'
        '</tr></thead><tbody>' + "".join(metric_rows) + "</tbody></table></div>"
    )


def render_phase5b1_dashboard(
    *, root: Path, current: dict[str, Any], quality: pd.DataFrame,
    input_audit: pd.DataFrame, monitoring: pd.DataFrame,
    decomposition: pd.DataFrame, data_status: pd.DataFrame,
    readiness: dict[str, Any], model_input_quality: pd.DataFrame,
    code_inventory: pd.DataFrame, git_state: dict[str, Any],
) -> Path:
    root = Path(root)
    nowcasts = pd.DataFrame(current["predictions"])
    uncertainty = current["uncertainty"]
    stage = current["operational_stage"]
    d = decomposition.iloc[0]
    default_horizon = stage["horizon"]
    p4_predictions = pd.read_parquet(root / "results/phase4c_holdout_predictions.parquet")
    p4_metrics = pd.read_parquet(root / "results/phase4c_holdout_metrics.parquet")

    warnings_html = "".join(
        f"<li>{escape(w)}</li>" for w in current["warnings"]
    ) or "<li>No operational warnings.</li>"

    blockers_html = "".join(
        f"<li>{escape(b)}</li>" for b in readiness["publication_blockers"]
    ) or "<li>None.</li>"

    quality_counts = quality["quality_status"].value_counts()

    quality_table = _table(quality, [
        ("variable_key", "Series"), ("quality_status", "Status"),
        ("latest_observation_date", "Latest"),
        ("expected_latest_observation_date", "Expected"),
        ("staleness_months", "Stale (months)"),
        ("missing_recent_12_months", "Missing, last 12m"),
        ("status_reasons", "Reason"),
    ])
    input_table = _table(input_audit, [
        ("model", "Model"), ("variable", "Exact input"),
        ("transformation", "Transformation"), ("lags_used", "Lags"),
        ("latest_usable_observation", "Latest usable"),
        ("effective_estimation_observations", "Effective N"),
        ("fallback_used", "Fallback"),
        ("model_passed_production_gate", "Gate"),
    ])
    monitoring_table = _table(monitoring, [
        ("model", "Model"), ("current_nowcast", "Nowcast"),
        ("historical_oos_rmse", "RMSE"), ("historical_oos_mae", "MAE"),
        ("historical_oos_bias", "Bias"),
        ("model_input_green_count", "Inputs GREEN"),
        ("model_input_amber_count", "Inputs AMBER"),
        ("model_input_red_count", "Inputs RED"),
        ("model_input_data_not_all_green", "Model-specific warning"),
        ("system_data_gate_has_warnings", "System warning"),
        ("monitoring_flags", "Flags"),
    ])
    model_input_table = _table(model_input_quality, [
        ("model", "Model"),
        ("input_keys", "Inputs consumed"),
        ("model_input_green_count", "GREEN"),
        ("model_input_amber_count", "AMBER"),
        ("model_input_red_count", "RED"),
        ("model_input_data_not_all_green", "Model-specific warning"),
    ])
    inventory_table = _table(
        code_inventory.loc[code_inventory["exists"]].assign(
            sha_short=lambda x: x["sha256"].str[:12]
        ),
        [
            ("file_path", "File"),
            ("role", "Role"),
            ("sha_short", "SHA-256 (short)"),
        ],
        limit=200,
    )

    recent_missing = data_status.loc[
        data_status["missing_value_classification"].isin([
            "true_missing_observation", "failed_data_retrieval",
            "deliberately_excluded_observation",
        ])
        & (pd.to_datetime(data_status["reference_period"]) >= pd.Timestamp("2026-07-01"))
    ]
    missing_table = _table(recent_missing, [
        ("variable_key", "Series"), ("reference_period", "Period"),
        ("missing_value_classification", "Classification"),
        ("quality_flag", "Quality flag"), ("reason", "Reason"),
    ], limit=40)

    dirty = git_state.get("working_tree_dirty")
    dirty_html = ", ".join(
        escape(p) for p in git_state.get("dirty_paths", [])[:6]
    ) + ("…" if len(git_state.get("dirty_paths", [])) > 6 else "")

    publication_pill_class = "ok" if readiness["publication_ready"] else "block"
    publication_pill_text = (
        "Publication ready" if readiness["publication_ready"]
        else "Blocked for official publication"
    )

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uzbekistan GDP Nowcast — Phase 5B.1</title><style>
:root{{--ink:#102a43;--muted:#627d98;--line:#d9e2ec;--bg:#f3f7f8;--paper:#fff;--teal:#0b6e69;--amber:#b7791f;--red:#b23a48;--green:#207a5a;--navy:#243b53}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.45}} .shell{{max-width:1180px;margin:auto;padding:28px 22px 64px}}
.mast{{background:linear-gradient(135deg,#102a43,#0b6e69);color:white;border-radius:20px;padding:34px 38px;box-shadow:0 16px 40px #102a4320}}
.eyebrow{{text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;opacity:.8;font-weight:700}} h1{{font-size:1.5rem;margin:7px 0 22px}}
.hero{{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:20px;align-items:end}}
.headline{{font-size:4.5rem;line-height:1;font-weight:760;letter-spacing:-.06em;margin:8px 0}} .headline small{{font-size:1.8rem}} .hero-cell{{border-left:1px solid #ffffff40;padding-left:18px}} .hero-cell b{{font-size:1.45rem;display:block;margin:4px 0}} .hero-note{{margin-top:20px;opacity:.82;font-size:.88rem}}
.section{{background:var(--paper);border:1px solid #e3ebf0;border-radius:16px;padding:25px 28px;margin-top:20px;box-shadow:0 8px 24px #102a4309}} .section h2{{font-size:1.12rem;margin:0 0 5px}} .lede{{color:var(--muted);margin:0 0 18px;font-size:.92rem}} .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} .metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .metric{{background:#f7fafb;border:1px solid var(--line);padding:14px;border-radius:12px}} .metric span{{display:block;color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}} .metric b{{font-size:1.5rem;display:block;margin-top:4px}}
.statusline{{display:inline-block;border-radius:20px;padding:5px 10px;font-size:.75rem;font-weight:750;background:#fff3cd;color:#835b00}}
.pill{{display:inline-block;border-radius:20px;padding:5px 10px;font-size:.75rem;font-weight:750}} .pill.ok{{background:#e7f6ef;color:#176b52}} .pill.block{{background:#fdeaea;color:#9b3d3d}}
.callout{{background:#fff9e8;border-left:4px solid var(--amber);padding:14px 16px;border-radius:0 10px 10px 0}} .callout.ok{{background:#e7f6ef;border-left-color:var(--green)}} .callout.block{{background:#fdeaea;border-left-color:var(--red)}}
ul{{padding-left:20px}}
.bar-row{{display:grid;grid-template-columns:190px 1fr 70px;gap:12px;align-items:center;margin:15px 0}} .bar-row.headline{{background:#e8f5f3;border-radius:10px;padding:11px;margin-left:-11px;margin-right:-11px}} .bar-label{{font-weight:600}} .bar-track{{height:12px;background:#edf2f5;border-radius:10px;overflow:hidden}} .bar-track span{{display:block;height:100%;border-radius:10px}} .bar-value{{text-align:right;font-weight:700}}
.revision{{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:center}} .revision .value{{font-size:2rem;font-weight:750}} .arrow{{font-size:1.8rem;color:var(--muted)}} .breakdown{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}} .breakdown div{{background:#f6f9fa;padding:12px;border-radius:10px;text-align:center}} .breakdown b{{display:block}}
.table-scroll{{overflow:auto}} table{{border-collapse:collapse;width:100%;font-size:.82rem}} th{{background:#f5f8fa;color:#486581;text-align:left}} th,td{{padding:9px 11px;border-bottom:1px solid #e6edf2;vertical-align:top}} td:not(:first-child),th:not(:first-child){{text-align:right}} details{{margin-top:12px}} summary{{cursor:pointer;font-weight:700;color:var(--navy)}} .technical details{{border-top:1px solid var(--line);padding-top:12px}} svg{{width:100%;height:auto}} .axis{{stroke:#bcccdc;stroke-width:1}} .svg-label{{font-size:12px;fill:#627d98}} .svg-value{{font-size:12px;font-weight:700;fill:#243b53}} .legend{{display:flex;gap:20px;justify-content:center;color:var(--muted);font-size:.8rem}} .legend i{{display:inline-block;width:10px;height:10px;margin-right:5px}}
.validation-control{{display:flex;gap:10px;align-items:center;margin-bottom:12px;color:var(--muted);font-size:.86rem}} select{{padding:7px;border:1px solid var(--line);border-radius:7px;background:#fff}} .highlight-row{{background:#e8f5f3;font-weight:650}} .subhead{{font-size:.95rem;margin:20px 0 8px}} footer{{color:#829ab1;text-align:center;font-size:.76rem;margin-top:24px}}
@media(max-width:820px){{.hero,.grid2,.metrics,.breakdown{{grid-template-columns:1fr}} .hero-cell{{border-left:0;border-top:1px solid #ffffff40;padding:12px 0 0}} .headline{{font-size:3.5rem}} .bar-row{{grid-template-columns:130px 1fr 60px}}}}
@media print{{body{{background:#fff}} .section,.mast{{box-shadow:none;break-inside:avoid}}}}
</style></head><body><main class="shell">

<header class="mast"><div class="eyebrow">Phase 5B.1 hardening patch · <span class="statusline">{escape(current['status'])}</span> · <span class="pill {publication_pill_class}">{escape(publication_pill_text)}</span></div>
<h1>Uzbekistan GDP Nowcast</h1>
<div class="hero">
<div><b>{escape(current['target']['target_quarter'])} NOWCAST</b>
<div class="headline">{current['point_nowcast']:.1f}<small>%</small></div>
<span>Real GDP growth, year on year</span></div>
<div class="hero-cell"><span>Operational stage</span><b>{escape(stage['horizon'])}</b><small>{escape(stage['reason'])}</small></div>
<div class="hero-cell"><span>80% empirical error range</span><b>{uncertainty['interval_80']['lower']:.2f}–{uncertainty['interval_80']['upper']:.2f}%</b><small>Empirical; not a conventional confidence interval</small></div>
<div class="hero-cell"><span>Latest official GDP</span><b>{current['latest_known_gdp_value']:.1f}%</b><small>{escape(current['latest_known_gdp_period'])}</small></div>
</div>
<div class="hero-note">As of / cutoff: {escape(current['information_cutoff'])} · Production combination: fixed 50/50 AR(2) + USD/UZS U-MIDAS(3) · Phase 5B headline reproduced within {current['phase5b_reference']['absolute_difference']:.2e}</div>
</header>

<section class="section"><h2>Publication readiness</h2>
<p class="lede">Analytical run success is not the same as publication readiness. Publication requires a clean git working tree so the commit alone identifies the code that produced the numbers.</p>
<div class="metrics">
<div class="metric"><span>Publication ready</span><b>{readiness['publication_ready']}</b></div>
<div class="metric"><span>Working tree dirty</span><b>{dirty}</b></div>
<div class="metric"><span>Code reproducibility complete</span><b>{readiness['code_reproducibility_complete']}</b></div>
<div class="metric"><span>Immutable upstream preserved</span><b>{readiness['immutable_upstream_artifacts_preserved']}</b></div>
</div>
<div class="callout {'ok' if readiness['publication_ready'] else 'block'}" style="margin-top:16px">
<b>{escape(publication_pill_text)}</b><br>
Git commit: <code>{escape(str(git_state.get('git_commit')))}</code><br>
Branch: <code>{escape(str(git_state.get('git_branch')))}</code><br>
Dirty paths (first 6): {dirty_html or '<i>none</i>'}<br>
Diff SHA-256: <code>{escape(str(git_state.get('diff_sha256')))}</code>
</div>
<h3 class="subhead">Publication blockers</h3>
<ul>{blockers_html}</ul>
</section>

<section class="section"><h2>What changed since the previous published run?</h2>
<p class="lede">No input vintage or model weight changed. Phase 5B corrected the stage label and used the matching frozen estimation path. Phase 5B.1 does not change the headline; it only adds auditability layers.</p>
<div class="revision">
<div><span>Previous nowcast (Phase 5A)</span><div class="value">{d['previous_nowcast']:.2f}%</div><small>Calendar-labelled H3</small></div>
<div class="arrow">→</div>
<div><span>Current nowcast (Phase 5B / 5B.1)</span><div class="value">{d['new_nowcast']:.2f}%</div><small>{d['total_revision']:+.2f} pp · availability-driven {escape(stage['horizon'])}</small></div>
</div>
<div class="breakdown">
<div>New-data effect<b>{float(d['new_data_effect'] or 0.0):+.2f} pp</b></div>
<div>Data-revision effect<b>{float(d['data_revision_effect'] or 0.0):+.2f} pp</b></div>
<div>Stage/specification effect<b>{float(d['model_specification_or_stage_effect'] or 0.0):+.2f} pp</b></div>
</div>
<p class="lede" style="margin-top:12px">Residual (total − explained) = <b>{float(d['residual']):+.2e}</b> pp; within 1e-10 tolerance: <b>{bool(d['residual_within_tolerance_1e_10'])}</b>.</p>
</section>

<div class="grid2">
<section class="section"><h2>Model-level nowcasts</h2>
<p class="lede">The highlighted estimate is the unchanged production combination.</p>
{_comparison_bars(nowcasts)}
</section>
<section class="section"><h2>Data gate (system vs model)</h2>
<p class="lede">Every registry series is checked. Only variables a model actually consumes contribute to its model-specific warning.</p>
<div class="metrics">
<div class="metric"><span>System green</span><b>{quality_counts.get('GREEN',0)}</b></div>
<div class="metric"><span>System amber</span><b>{quality_counts.get('AMBER',0)}</b></div>
<div class="metric"><span>System red</span><b>{quality_counts.get('RED',0)}</b></div>
<div class="metric"><span>Fallbacks</span><b>{current['fallback_observations_used']}</b></div>
</div>
<h3 class="subhead">Per-model input quality</h3>
{model_input_table}
</section>
</div>

<section class="section"><h2>Important warnings</h2>
<div class="callout"><ul>{warnings_html}</ul></div>
<p class="lede" style="margin-top:12px"><b>New information since previous run:</b> none; the master and registry hashes are unchanged.</p>
</section>

<section class="section"><h2>Uncertainty and historical performance</h2>
<p class="lede">{escape(uncertainty['presentation_note'])}</p>
<div class="metrics">
<div class="metric"><span>Point nowcast</span><b>{current['point_nowcast']:.2f}%</b></div>
<div class="metric"><span>50% empirical range</span><b>{uncertainty['interval_50']['lower']:.2f}–{uncertainty['interval_50']['upper']:.2f}%</b></div>
<div class="metric"><span>80% empirical range</span><b>{uncertainty['interval_80']['lower']:.2f}–{uncertainty['interval_80']['upper']:.2f}%</b></div>
<div class="metric"><span>Historical {escape(stage['horizon'])} RMSE</span><b>{uncertainty['historical_rmse']:.3f}</b></div>
</div>
<p class="lede" style="margin-top:12px">Historical {escape(stage['horizon'])} bias (actual − forecast): <b>{uncertainty['historical_h2_bias_actual_minus_forecast']:+.3f} pp</b>. The 50% range is not necessarily centered on the point estimate because the historical error distribution is asymmetric.</p>
<div style="margin-top:20px">{_actual_vs_nowcast(p4_predictions)}</div>
</section>

<section class="section"><h2>Frozen validation</h2>
<p class="lede">Default horizon is the current operational stage ({escape(default_horizon)}). H1 and H3 remain selectable.</p>
{_validation_tables(p4_predictions, p4_metrics, default_horizon)}
</section>

<section class="section technical"><h2>Technical audit</h2>
<p class="lede">Expandable evidence for reviewers and operators.</p>
<details><summary>Exact model inputs</summary>{input_table}</details>
<details><summary>Source freshness and quality gate</summary>{quality_table}</details>
<details><summary>Recent missing, partial, failed, or excluded observations</summary>{missing_table}</details>
<details><summary>Model monitoring (system vs model-specific)</summary>{monitoring_table}</details>
<details><summary>Production code hash inventory</summary>{inventory_table}</details>
<details><summary>Publication policy and methodology</summary>
<p>Target: real GDP YoY. Estimation: expanding window. Information rule: assumed release date must not exceed the forecast origin or run cutoff. Stage depends on complete contiguous target-quarter USD/UZS aggregates. The ensemble is always 0.5 AR(2) + 0.5 U-MIDAS(3). No model is removed merely for disagreement. No imputation is permitted.</p>
<p>Publication readiness is stricter than analytical run success. A run intended for official publication requires a clean git working tree, a passing data gate, an available headline model, cutoff integrity, and preserved upstream artifacts. Analytical runs may proceed with SUCCESS_WITH_WARNINGS.</p>
</details>
</section>

<footer>Phase 5B.1 · Run {escape(current['run_id'])} · Hardening patch · Forecasts are estimates, not official statistics.</footer>
</main>
<script>
const s=document.getElementById('horizon-select');
if(s){{s.addEventListener('change',()=>document.querySelectorAll('.validation-panel').forEach(p=>p.style.display=p.dataset.horizon===s.value?'block':'none'))}}
</script>
</body></html>"""
    path = root / "dashboard/phase5b1_uzbekistan_nowcast.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
