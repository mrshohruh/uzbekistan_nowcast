"""Self-contained management dashboard rendering for Phase 5A."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


LABELS = {
    "historical_mean": "Historical mean",
    "ar1": "AR(1)",
    "ar2": "AR(2)",
    "umidas_usd_uzs_mom_dlog": "USD/UZS U-MIDAS",
    "ensemble_ar2_umidas_usd": "50/50 ensemble",
}
COLORS = {
    "ar1": "#6f8092",
    "ar2": "#334e68",
    "umidas_usd_uzs_mom_dlog": "#28a5a5",
    "ensemble_ar2_umidas_usd": "#0b6e69",
    "actual": "#cf7a28",
}


def _fmt(value: Any, decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    return f"{float(value):.{decimals}f}"


def _comparison_bars(nowcasts: pd.DataFrame) -> str:
    max_value = max(float(nowcasts["prediction"].max()), 0.1)
    rows = []
    for row in nowcasts.itertuples(index=False):
        width = max(4.0, 100.0 * float(row.prediction) / max_value)
        headline = " headline" if row.production_headline_flag else ""
        rows.append(
            f'<div class="bar-row{headline}"><div class="bar-label">{escape(LABELS[row.model])}</div>'
            f'<div class="bar-track"><span style="width:{width:.1f}%;background:{COLORS[row.model]}"></span></div>'
            f'<div class="bar-value">{row.prediction:.2f}%</div></div>'
        )
    return "".join(rows)


def _svg_polyline(values: list[float], labels: list[str], *, width: int = 720,
                  height: int = 220, color: str = "#0b6e69") -> str:
    left, right, top, bottom = 48, 18, 20, 42
    plot_w, plot_h = width - left - right, height - top - bottom
    low = min(values) - 0.35
    high = max(values) + 0.35
    span = max(high - low, 1.0)
    xs = [left + i * plot_w / max(len(values) - 1, 1) for i in range(len(values))]
    ys = [top + (high - v) * plot_h / span for v in values]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    marks = []
    for x, y, label, value in zip(xs, ys, labels, values):
        marks.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" />'
            f'<text x="{x:.1f}" y="{y-11:.1f}" text-anchor="middle" class="svg-value">{value:.2f}</text>'
            f'<text x="{x:.1f}" y="{height-15}" text-anchor="middle" class="svg-label">{escape(label)}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Forecast evolution chart">'
        f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" class="axis" />'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />'
        + "".join(marks) + "</svg>"
    )


def _historical_evolution(updates: pd.DataFrame) -> str:
    block = updates.loc[
        (updates["model"] == "ensemble_ar2_umidas_usd")
        & (updates["lag_mode"] == "standard")
    ].sort_values("target_quarter")
    cards = []
    for row in block.itertuples(index=False):
        values = [row.H1_prediction, row.H2_prediction, row.H3_prediction, row.actual]
        cards.append(
            f'<article class="evolution-card"><h3>{escape(str(row.target_quarter))}</h3>'
            f'{_svg_polyline(values, ["H1", "H2", "H3", "Actual"], width=460, height=190)}'
            f'</article>'
        )
    return "".join(cards)


def _actual_vs_nowcast(predictions: pd.DataFrame) -> str:
    block = predictions.loc[
        (predictions["model"] == "ensemble_ar2_umidas_usd")
        & (predictions["lag_mode"] == "standard")
        & (predictions["horizon"] == "H3")
    ].sort_values("target_quarter")
    width, height = 760, 250
    left, right, top, bottom = 48, 20, 22, 50
    plot_w, plot_h = width-left-right, height-top-bottom
    high = max(float(block[["actual", "prediction"]].max().max()) + 0.8, 1.0)
    groups = []
    for i, row in enumerate(block.itertuples(index=False)):
        center = left + (i + .5) * plot_w / len(block)
        for j, (name, value, color) in enumerate((
            ("Nowcast", row.prediction, COLORS["ensemble_ar2_umidas_usd"]),
            ("Actual", row.actual, COLORS["actual"]),
        )):
            bar_w = 28
            x = center + (-20 if j == 0 else 20) - bar_w/2
            y = top + (high-float(value))*plot_h/high
            h = top+plot_h-y
            groups.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" rx="4" fill="{color}" />'
                f'<text x="{x+bar_w/2:.1f}" y="{y-7:.1f}" text-anchor="middle" class="svg-value">{float(value):.2f}</text>'
            )
        groups.append(
            f'<text x="{center:.1f}" y="{height-18}" text-anchor="middle" class="svg-label">{escape(str(row.target_quarter))}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Actual GDP versus frozen H3 ensemble forecasts">'
        f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" class="axis" />'
        + "".join(groups) + "</svg>"
        '<div class="legend"><span><i style="background:#0b6e69"></i>H3 ensemble nowcast</span>'
        '<span><i style="background:#cf7a28"></i>Official GDP</span></div>'
    )


def _validation_tables(predictions: pd.DataFrame, metrics: pd.DataFrame) -> str:
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
            f'<div class="validation-panel" data-horizon="{horizon}" style="display:{"block" if horizon == "H3" else "none"}">'
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
    return (
        '<div class="validation-control"><label for="horizon-select">Quarter table horizon</label>'
        '<select id="horizon-select"><option>H1</option><option>H2</option><option selected>H3</option></select></div>'
        + "".join(pieces)
        + '<h3 class="subhead">RMSE by horizon</h3><div class="table-scroll"><table><thead><tr>'
        '<th>Frozen model</th><th>H1</th><th>H2</th><th>H3</th><th>Pooled H1–H3</th>'
        '</tr></thead><tbody>' + "".join(metric_rows) + "</tbody></table></div>"
    )


def _availability_table(availability: dict[str, Any]) -> str:
    rows = []
    for item in availability["indicator_summary"]:
        status = item["indicator_status"]
        label = {
            "available": "Available",
            "awaiting_release": "Awaiting release",
            "missing_unavailable": "Missing / unavailable",
        }[status]
        rows.append(
            f'<tr><td>{escape(item["variable_key"])}</td>'
            f'<td>{escape(str(item["most_recent_usable_reference_period"] or "—"))}</td>'
            f'<td><span class="status {status}">{label}</span></td></tr>'
        )
    return "".join(rows)


def render_dashboard(
    *, root: Path, nowcasts: pd.DataFrame, target: dict[str, Any],
    horizon_state: dict[str, str], availability: dict[str, Any],
    uncertainty: dict[str, Any], data_status: pd.DataFrame,
) -> Path:
    """Render a standalone HTML dashboard using only generated artifacts."""
    root = Path(root)
    p4_predictions = pd.read_parquet(root / "results/phase4c_holdout_predictions.parquet")
    p4_metrics = pd.read_parquet(root / "results/phase4c_holdout_metrics.parquet")
    p4_updates = pd.read_parquet(root / "results/phase4c_horizon_updates.parquet")
    headline = nowcasts.loc[nowcasts["production_headline_flag"]].iloc[0]
    components = nowcasts.set_index("model")["prediction"]
    if uncertainty.get("reported"):
        range_text = (
            f'{uncertainty["lower"]:.2f}% to {uncertainty["upper"]:.2f}%'
        )
        range_note = (
            f'Indicative only: headline ± {uncertainty["development_rmse"]:.3f} percentage points, '
            f'based on {uncertainty["n_development_forecasts"]} matching Phase 4B development forecasts.'
        )
    else:
        range_text = "Not reported"
        range_note = escape(str(uncertainty.get("reason", "Insufficient development evidence.")))
    date_label = pd.Timestamp(headline["as_of_date"]).strftime("%d %B %Y")
    current_evolution = _svg_polyline(
        [float(headline["prediction"])], [headline["horizon"]], width=560, height=190
    )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uzbekistan Real GDP Nowcast — {escape(target['target_quarter'])}</title>
<style>
:root{{--ink:#102a43;--muted:#627d98;--line:#d9e2ec;--paper:#fff;--bg:#f3f7f8;--teal:#0b6e69;--teal2:#28a5a5;--orange:#cf7a28;--navy:#243b53}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.45}}
.shell{{max-width:1180px;margin:auto;padding:28px 22px 60px}} .mast{{background:linear-gradient(135deg,#102a43,#0b6e69);color:#fff;border-radius:20px;padding:34px 38px;box-shadow:0 16px 40px #102a4320}}
.eyebrow{{font-size:.75rem;letter-spacing:.13em;text-transform:uppercase;opacity:.78;font-weight:700}} h1{{font-size:1.45rem;margin:7px 0 24px;font-weight:650}} .hero-grid{{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:24px;align-items:end}}
.quarter{{font-size:1.1rem;font-weight:750;letter-spacing:.04em}} .headline-number{{font-size:4.5rem;line-height:1;font-weight:760;letter-spacing:-.06em;margin:8px 0}} .headline-number small{{font-size:1.8rem}}
.hero-stat{{border-left:1px solid #ffffff42;padding-left:22px}} .hero-stat b{{font-size:1.55rem;display:block;margin-top:4px}} .hero-note{{margin-top:22px;font-size:.9rem;opacity:.84}}
.section{{background:var(--paper);border:1px solid #e3ebf0;border-radius:16px;padding:25px 28px;margin-top:20px;box-shadow:0 8px 24px #102a4309}} .section h2{{font-size:1.12rem;margin:0 0 5px}} .lede{{color:var(--muted);margin:0 0 20px;font-size:.93rem}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} .metric-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .metric{{background:#f7fafb;border:1px solid var(--line);border-radius:12px;padding:15px}} .metric span{{font-size:.76rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}} .metric b{{font-size:1.6rem;display:block;margin-top:4px}}
.bar-row{{display:grid;grid-template-columns:190px 1fr 70px;gap:12px;align-items:center;margin:16px 0}} .bar-row.headline{{background:#e8f5f3;border-radius:10px;padding:12px;margin-left:-12px;margin-right:-12px}} .bar-label{{font-weight:600}} .bar-track{{height:12px;background:#edf2f5;border-radius:10px;overflow:hidden}} .bar-track span{{display:block;height:100%;border-radius:10px}} .bar-value{{font-variant-numeric:tabular-nums;text-align:right;font-weight:700}}
.driver{{border:1px solid var(--line);border-radius:14px;padding:20px;background:#fbfdfd}} .formula{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:10px;align-items:center;text-align:center;margin:22px 0}} .formula .box{{padding:16px 8px;background:#f0f6f7;border-radius:10px}} .formula b{{display:block;font-size:1.35rem}} .op{{color:var(--muted);font-weight:700}}
.evolution-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} .evolution-card{{border:1px solid var(--line);border-radius:12px;padding:12px}} .evolution-card h3{{margin:0 0 4px;font-size:.95rem}} svg{{width:100%;height:auto}} .axis{{stroke:#bcccdc;stroke-width:1}} .svg-label{{font-size:12px;fill:#627d98}} .svg-value{{font-size:12px;font-weight:700;fill:#243b53}} .legend{{display:flex;gap:22px;justify-content:center;color:var(--muted);font-size:.82rem}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}}
.table-scroll{{overflow:auto}} table{{border-collapse:collapse;width:100%;font-size:.86rem}} th{{text-align:left;color:#486581;font-weight:650;background:#f5f8fa}} th,td{{padding:10px 12px;border-bottom:1px solid #e7edf2;white-space:nowrap}} td:not(:first-child),th:not(:first-child){{text-align:right;font-variant-numeric:tabular-nums}} .highlight-row{{background:#e8f5f3;font-weight:650}} .subhead{{font-size:.95rem;margin:23px 0 8px}} .validation-control{{display:flex;gap:10px;align-items:center;margin-bottom:12px;color:var(--muted);font-size:.86rem}} select{{padding:7px 10px;border:1px solid #bcccdc;border-radius:7px;background:#fff}}
.status{{font-size:.72rem;font-weight:700;border-radius:20px;padding:4px 8px}} .available{{color:#176b52;background:#e3f5ed}} .awaiting_release{{color:#8a5b00;background:#fff3cd}} .missing_unavailable{{color:#9b3d3d;background:#fdeaea}} .callout{{border-left:4px solid var(--teal);background:#eef8f7;padding:14px 17px;border-radius:0 10px 10px 0;color:#334e68}} details{{color:#486581}} details summary{{cursor:pointer;font-weight:650;color:#243b53}} footer{{color:#829ab1;font-size:.76rem;margin-top:24px;text-align:center}}
@media(max-width:780px){{.hero-grid,.grid-2,.metric-grid,.evolution-grid{{grid-template-columns:1fr}} .hero-stat{{border-left:0;border-top:1px solid #ffffff42;padding:14px 0 0}} .headline-number{{font-size:3.6rem}} .bar-row{{grid-template-columns:130px 1fr 60px}} .formula{{grid-template-columns:1fr}} .op{{transform:rotate(90deg)}}}}
@media print{{body{{background:#fff}} .section,.mast{{box-shadow:none;break-inside:avoid}} .shell{{max-width:none}}}}
</style></head><body><main class="shell">
<header class="mast"><div class="eyebrow">Operational prototype · standard release-lag convention</div><h1>Uzbekistan Real GDP Nowcast</h1>
<div class="hero-grid"><div><div class="quarter">{escape(target['target_quarter'])} NOWCAST</div><div class="headline-number">{headline['prediction']:.1f}<small>%</small></div><div>Real GDP growth, year on year</div></div>
<div class="hero-stat"><span>Current information stage</span><b>{escape(horizon_state['horizon'])}</b><small>{escape(horizon_state['reason'])}</small></div>
<div class="hero-stat"><span>Latest official GDP</span><b>{target['latest_known_gdp_growth']:.1f}%</b><small>{escape(target['latest_known_gdp_quarter'])}</small></div></div>
<div class="hero-note">Updated: {date_label} · Latest usable monthly reference period: {escape(str(availability['latest_usable_monthly_reference_period']))}</div></header>

<section class="section"><h2>Forecast comparison</h2><p class="lede">Four frozen specifications, re-estimated on the expanding information set. The ensemble is the fixed production headline.</p>{_comparison_bars(nowcasts)}
<div class="callout"><b>{escape(str(uncertainty.get('label','Uncertainty range'))).capitalize()}: {range_text}</b><br>{range_note} This is not a formal confidence interval.</div></section>

<div class="grid-2"><section class="section"><h2>Current nowcast evolution</h2><p class="lede">The initial live run contains the current {escape(horizon_state['horizon'])} stage. Future runs will add operational revisions.</p>{current_evolution}</section>
<section class="section"><h2>Forecast drivers</h2><p class="lede">Current high-frequency production signal: USD/UZS monthly dynamics.</p><div class="formula"><div class="box">AR(2)<b>{components['ar2']:.2f}%</b><small>GDP persistence</small></div><div class="op">× 0.5 +</div><div class="box">U-MIDAS<b>{components['umidas_usd_uzs_mom_dlog']:.2f}%</b><small>Monthly FX signal</small></div><div class="op">× 0.5 =</div><div class="box">Headline<b>{components['ensemble_ar2_umidas_usd']:.2f}%</b><small>Fixed combination</small></div></div><p class="lede">The component estimates are predictive signals, not causal contributions. No sector effects are inferred.</p></section></div>

<section class="section"><h2>How nowcasts evolved in frozen validation</h2><p class="lede">Each line moves from the first to the third within-quarter information stage, then compares with the subsequently observed GDP outcome.</p><div class="evolution-grid">{_historical_evolution(p4_updates)}</div></section>

<section class="section"><h2>Actual versus nowcast</h2><p class="lede">Genuine frozen out-of-sample H3 ensemble forecasts; no development fitted values are mixed into this chart.</p>{_actual_vs_nowcast(p4_predictions)}</section>

<section class="section"><h2>Model validation</h2><p class="lede"><b>Frozen validation: 2025Q3–2026Q2.</b> Validation contains four quarters; results should be interpreted as initial out-of-sample evidence rather than definitive statistical ranking.</p>{_validation_tables(p4_predictions,p4_metrics)}</section>

<section class="section"><h2>Data availability</h2><p class="lede">Availability is evaluated cell by cell from registry release lags. A September master row is not treated as observed merely because the row exists.</p>
<div class="metric-grid"><div class="metric"><span>Registered indicators</span><b>{availability['registered_indicators']}</b></div><div class="metric"><span>Currently usable</span><b>{availability['currently_usable_indicators']}</b></div><div class="metric"><span>Awaiting release</span><b>{availability['awaiting_release_indicators']}</b></div><div class="metric"><span>Missing / unavailable</span><b>{availability['missing_unavailable_indicators']}</b></div></div>
<details style="margin-top:18px"><summary>Indicator-level status and latest usable observation</summary><div class="table-scroll"><table><thead><tr><th>Indicator</th><th>Latest usable reference period</th><th>Status</th></tr></thead><tbody>{_availability_table(availability)}</tbody></table></div></details></section>

<section class="section"><details><summary>Methodology and governance</summary><p>GDP target: real GDP year-on-year growth. Primary production model: fixed 50/50 AR(2) plus USD/UZS U-MIDAS(3). Information timing follows registry-based standard release lags. Estimation uses an expanding window and excludes the target and all later GDP outcomes. Phase 4C contains four untouched validation quarters, and the architecture was not changed after holdout opening.</p><p>{escape(target['reason'])}</p></details></section>
<footer>Phase 5A operational prototype · Generated from machine-readable Phase 4 and Phase 5 artifacts · Forecasts are estimates, not official statistics.</footer>
</main><script>
const select=document.getElementById('horizon-select');
select.addEventListener('change',()=>document.querySelectorAll('.validation-panel').forEach(p=>p.style.display=p.dataset.horizon===select.value?'block':'none'));
</script></body></html>"""
    output = root / "dashboard/phase5a_uzbekistan_nowcast.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output
