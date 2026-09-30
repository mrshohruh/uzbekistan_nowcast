"""Management-facing, self-contained Phase 5B HTML dashboard."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from uznowcast.operational.dashboard import (
    LABELS, _actual_vs_nowcast, _comparison_bars, _validation_tables,
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
            elif value is None or pd.isna(value):
                text = "—"
            else:
                text = str(value)
            cells.append(f"<td>{escape(text)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def render_phase5b_dashboard(
    *, root: Path, current: dict[str, Any], quality: pd.DataFrame,
    input_audit: pd.DataFrame, monitoring: pd.DataFrame,
    decomposition: pd.DataFrame, data_status: pd.DataFrame,
) -> Path:
    root = Path(root)
    nowcasts = pd.DataFrame(current["predictions"])
    uncertainty = current["uncertainty"]
    stage = current["operational_stage"]
    d = decomposition.iloc[0]
    p4_predictions = pd.read_parquet(root / "results/phase4c_holdout_predictions.parquet")
    p4_metrics = pd.read_parquet(root / "results/phase4c_holdout_metrics.parquet")
    warnings = "".join(f"<li>{escape(w)}</li>" for w in current["warnings"])
    quality_counts = quality["quality_status"].value_counts()
    recent_missing = data_status.loc[
        data_status["missing_value_classification"].isin([
            "true_missing_observation", "failed_data_retrieval",
            "deliberately_excluded_observation",
        ])
        & (pd.to_datetime(data_status["reference_period"]) >= pd.Timestamp("2026-07-01"))
    ]
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
        ("deviation_from_ensemble", "Vs ensemble"),
        ("estimation_sample_size", "Estimation N"),
        ("monitoring_flags", "Flags"),
    ])
    missing_table = _table(recent_missing, [
        ("variable_key", "Series"), ("reference_period", "Period"),
        ("missing_value_classification", "Classification"),
        ("quality_flag", "Quality flag"), ("reason", "Reason"),
    ], limit=40)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uzbekistan GDP Nowcast — Phase 5B</title><style>
:root{{--ink:#102a43;--muted:#627d98;--line:#d9e2ec;--bg:#f3f7f8;--paper:#fff;--teal:#0b6e69;--amber:#b7791f;--red:#b23a48;--green:#207a5a;--navy:#243b53}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.45}} .shell{{max-width:1180px;margin:auto;padding:28px 22px 64px}}
.mast{{background:linear-gradient(135deg,#102a43,#0b6e69);color:white;border-radius:20px;padding:34px 38px;box-shadow:0 16px 40px #102a4320}} .eyebrow{{text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;opacity:.8;font-weight:700}} h1{{font-size:1.5rem;margin:7px 0 22px}} .hero{{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:20px;align-items:end}} .headline{{font-size:4.5rem;line-height:1;font-weight:760;letter-spacing:-.06em;margin:8px 0}} .headline small{{font-size:1.8rem}} .hero-cell{{border-left:1px solid #ffffff40;padding-left:18px}} .hero-cell b{{font-size:1.45rem;display:block;margin:4px 0}} .hero-note{{margin-top:20px;opacity:.82;font-size:.88rem}}
.section{{background:var(--paper);border:1px solid #e3ebf0;border-radius:16px;padding:25px 28px;margin-top:20px;box-shadow:0 8px 24px #102a4309}} .section h2{{font-size:1.12rem;margin:0 0 5px}} .lede{{color:var(--muted);margin:0 0 18px;font-size:.92rem}} .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} .metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .metric{{background:#f7fafb;border:1px solid var(--line);padding:14px;border-radius:12px}} .metric span{{display:block;color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}} .metric b{{font-size:1.5rem;display:block;margin-top:4px}}
.statusline{{display:inline-block;border-radius:20px;padding:5px 10px;font-size:.75rem;font-weight:750;background:#fff3cd;color:#835b00}} .callout{{background:#fff9e8;border-left:4px solid var(--amber);padding:14px 16px;border-radius:0 10px 10px 0}} .ok{{background:#e7f6ef;border-left-color:var(--green)}} ul{{padding-left:20px}}
.bar-row{{display:grid;grid-template-columns:190px 1fr 70px;gap:12px;align-items:center;margin:15px 0}} .bar-row.headline{{background:#e8f5f3;border-radius:10px;padding:11px;margin-left:-11px;margin-right:-11px}} .bar-label{{font-weight:600}} .bar-track{{height:12px;background:#edf2f5;border-radius:10px;overflow:hidden}} .bar-track span{{display:block;height:100%;border-radius:10px}} .bar-value{{text-align:right;font-weight:700}}
.revision{{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:center}} .revision .value{{font-size:2rem;font-weight:750}} .arrow{{font-size:1.8rem;color:var(--muted)}} .breakdown{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}} .breakdown div{{background:#f6f9fa;padding:12px;border-radius:10px;text-align:center}} .breakdown b{{display:block}}
.table-scroll{{overflow:auto}} table{{border-collapse:collapse;width:100%;font-size:.82rem}} th{{background:#f5f8fa;color:#486581;text-align:left}} th,td{{padding:9px 11px;border-bottom:1px solid #e6edf2;vertical-align:top}} td:not(:first-child),th:not(:first-child){{text-align:right}} details{{margin-top:12px}} summary{{cursor:pointer;font-weight:700;color:var(--navy)}} .technical details{{border-top:1px solid var(--line);padding-top:12px}} svg{{width:100%;height:auto}} .axis{{stroke:#bcccdc;stroke-width:1}} .svg-label{{font-size:12px;fill:#627d98}} .svg-value{{font-size:12px;font-weight:700;fill:#243b53}} .legend{{display:flex;gap:20px;justify-content:center;color:var(--muted);font-size:.8rem}} .legend i{{display:inline-block;width:10px;height:10px;margin-right:5px}}
.validation-control{{display:flex;gap:10px;align-items:center;margin-bottom:12px;color:var(--muted);font-size:.86rem}} select{{padding:7px;border:1px solid var(--line);border-radius:7px;background:#fff}} .highlight-row{{background:#e8f5f3;font-weight:650}} .subhead{{font-size:.95rem;margin:20px 0 8px}} footer{{color:#829ab1;text-align:center;font-size:.76rem;margin-top:24px}}
@media(max-width:820px){{.hero,.grid2,.metrics,.breakdown{{grid-template-columns:1fr}} .hero-cell{{border-left:0;border-top:1px solid #ffffff40;padding:12px 0 0}} .headline{{font-size:3.5rem}} .bar-row{{grid-template-columns:130px 1fr 60px}}}}
@media print{{body{{background:#fff}} .section,.mast{{box-shadow:none;break-inside:avoid}}}}</style></head><body><main class="shell">
<header class="mast"><div class="eyebrow">Hardened operational run · <span class="statusline">{escape(current['status'])}</span></div><h1>Uzbekistan GDP Nowcast</h1><div class="hero"><div><b>{escape(current['target']['target_quarter'])} NOWCAST</b><div class="headline">{current['point_nowcast']:.1f}<small>%</small></div><span>Real GDP growth, year on year</span></div><div class="hero-cell"><span>Operational stage</span><b>{escape(stage['horizon'])}</b><small>{escape(stage['reason'])}</small></div><div class="hero-cell"><span>80% error range</span><b>{uncertainty['interval_80']['lower']:.2f}–{uncertainty['interval_80']['upper']:.2f}%</b><small>Empirical; not a confidence interval</small></div><div class="hero-cell"><span>Latest official GDP</span><b>{current['latest_known_gdp_value']:.1f}%</b><small>{escape(current['latest_known_gdp_period'])}</small></div></div><div class="hero-note">As of / cutoff: {escape(current['information_cutoff'])} · Production combination: fixed 50/50 AR(2) + USD/UZS U-MIDAS(3)</div></header>

<section class="section"><h2>What changed since the previous published run?</h2><p class="lede">No input vintage or model weight changed. Phase 5B corrected the stage label and used the matching frozen estimation path.</p><div class="revision"><div><span>Previous nowcast</span><div class="value">{d['previous_nowcast']:.2f}%</div><small>Phase 5A, calendar-labelled H3</small></div><div class="arrow">→</div><div><span>Current nowcast</span><div class="value">{d['new_nowcast']:.2f}%</div><small>{d['total_revision']:+.2f} percentage points · availability-driven {escape(stage['horizon'])}</small></div></div><div class="breakdown"><div>New-data effect<b>{d['new_data_effect']:+.2f} pp</b></div><div>Data-revision effect<b>{d['data_revision_effect']:+.2f} pp</b></div><div>Stage/specification effect<b>{d['model_specification_or_stage_effect']:+.2f} pp</b></div></div></section>

<div class="grid2"><section class="section"><h2>Model-level nowcasts</h2><p class="lede">The highlighted estimate is the unchanged production combination.</p>{_comparison_bars(nowcasts)}</section><section class="section"><h2>Data gate</h2><p class="lede">All 29 registry series are checked; only GDP and USD/UZS are required by the frozen production models.</p><div class="metrics"><div class="metric"><span>Green</span><b>{quality_counts.get('GREEN',0)}</b></div><div class="metric"><span>Amber</span><b>{quality_counts.get('AMBER',0)}</b></div><div class="metric"><span>Red</span><b>{quality_counts.get('RED',0)}</b></div><div class="metric"><span>Fallbacks</span><b>{current['fallback_observations_used']}</b></div></div><p class="lede" style="margin-top:14px">September USD/UZS is partial in this vintage and is deliberately excluded. No observation is filled or fabricated.</p></section></div>

<section class="section"><h2>Important warnings</h2><div class="callout"><ul>{warnings or '<li>No operational warnings.</li>'}</ul></div><p class="lede" style="margin-top:12px"><b>New information since previous run:</b> none; the master and registry hashes are unchanged.</p></section>

<section class="section"><h2>Uncertainty and historical performance</h2><p class="lede">The 50% and 80% ranges are empirical actual-minus-forecast error quantiles from {uncertainty['sample_size']} matching-{escape(stage['horizon'])} pre-current forecasts. They are not structural probability forecasts.</p><div class="metrics"><div class="metric"><span>Point nowcast</span><b>{current['point_nowcast']:.2f}%</b></div><div class="metric"><span>50% range</span><b>{uncertainty['interval_50']['lower']:.2f}–{uncertainty['interval_50']['upper']:.2f}%</b></div><div class="metric"><span>80% range</span><b>{uncertainty['interval_80']['lower']:.2f}–{uncertainty['interval_80']['upper']:.2f}%</b></div><div class="metric"><span>Historical RMSE</span><b>{uncertainty['historical_rmse']:.3f}</b></div></div><div style="margin-top:20px">{_actual_vs_nowcast(p4_predictions)}</div></section>

<section class="section"><h2>Frozen validation</h2><p class="lede">2025Q3–2026Q2; four untouched quarters. Interpret as initial evidence, not a definitive ranking.</p>{_validation_tables(p4_predictions,p4_metrics)}</section>

<section class="section technical"><h2>Technical audit</h2><p class="lede">Expandable evidence for reviewers and operators.</p><details><summary>Exact model inputs</summary>{input_table}</details><details><summary>Source freshness and quality gate</summary>{quality_table}</details><details><summary>Recent missing, partial, failed, or excluded observations</summary>{missing_table}</details><details><summary>Model monitoring</summary>{monitoring_table}</details><details><summary>Production policy and methodology</summary><p>Target: real GDP YoY. Estimation: expanding window. Information rule: assumed release date must not exceed the forecast origin or run cutoff. Stage depends on complete contiguous target-quarter USD/UZS aggregates. The ensemble is always 0.5 AR(2) + 0.5 U-MIDAS(3). No model is removed merely for disagreement. No imputation is permitted.</p></details></section>
<footer>Phase 5B · Run {escape(current['run_id'])} · Self-contained operational artifact · Forecasts are estimates, not official statistics.</footer></main><script>const s=document.getElementById('horizon-select');if(s){{s.addEventListener('change',()=>document.querySelectorAll('.validation-panel').forEach(p=>p.style.display=p.dataset.horizon===s.value?'block':'none'))}}</script></body></html>"""
    path = root / "dashboard/phase5b_uzbekistan_nowcast.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
