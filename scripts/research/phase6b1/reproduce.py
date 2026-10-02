"""Reproduce the immutable Phase 6B GDP leak before implementing its repair."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
OUT = ROOT/'results/research/phase6b1'


def old_core():
    path = ROOT/'scripts/research/phase6b/experiment.py'
    spec = importlib.util.spec_from_file_location('immutable_phase6b_core', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def demonstrate():
    import pandas as pd
    from uznowcast.models.data import load_dataset, horizon_month_end, quarter_end
    target, horizon, mode = '2024Q2', 'H1', 'standard'
    core = old_core()
    dataset = load_dataset(ROOT)
    prior = str(pd.Period(target, freq='Q')-1)
    origin = horizon_month_end(target,horizon)
    assumed_date = quarter_end(prior)+pd.Timedelta(days=dataset.release_lag_days['gdp_real_yoy'])
    assert assumed_date > origin
    states = pd.read_csv(ROOT/'results/research/phase6b/phase6b_factor_series.csv')
    rows = states.loc[states.specification.eq('DFM_DOMESTIC_3') & states.target_quarter.eq(target) &
                      states.horizon.eq(horizon) & states.lag_mode.eq(mode) & states.factor.eq(1)].sort_values('month')
    factors = rows.value.to_numpy().reshape(-1,1)
    index = pd.DatetimeIndex(pd.to_datetime(rows.month))
    gdp = dataset.gdp.set_index('quarter').gdp_real_yoy_pct
    training = gdp.loc[gdp.index<target].copy()
    old_value = float(training.loc[prior])
    baseline = core.bridge(factors,index,training,target,'BRIDGE_B')[0]
    training.loc[prior] = 999999.
    mutated = core.bridge(factors,index,training,target,'BRIDGE_B')[0]
    assert abs(mutated-baseline)>1e-5
    return dict(target_quarter=target,horizon=horizon,lag_mode=mode,forecast_origin_date=str(origin.date()),
                prior_quarter=prior,prior_original_GDP=old_value,mutated_GDP=999999.,
                prior_assumed_available_date=str(assumed_date.date()),prior_available_under_registry_rule=False,
                exact_historical_release_verified=False,release_quality='APPROXIMATE_FALLBACK',
                prediction_before=baseline,prediction_after=mutated,difference=mutated-baseline,
                status='LEAK_CONFIRMED', interpretation='Confirmed under registry timing; actual first release is unknown',
                original_code_sha256=hashlib.sha256((ROOT/'scripts/research/phase6b/experiment.py').read_bytes()).hexdigest())


if __name__ == '__main__':
    import pandas as pd
    result=demonstrate()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'phase6b1_leak_reproduction.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    pd.DataFrame([result]).to_csv(OUT/'phase6b1_leak_reproduction.csv',index=False)
