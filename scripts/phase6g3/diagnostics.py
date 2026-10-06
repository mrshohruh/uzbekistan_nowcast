"""Ex-post economic associations; never add a predictor to factor estimation."""
import json
import numpy as np
import pandas as pd
from scripts.phase6e.models import FIELDS


def economic_diagnostics(gdp,panel,dataset,factors):
    rows=[]
    targets=gdp.set_index('quarter',drop=False) if gdp.index.name!='quarter' else gdp
    targets=targets[['nominal_gdp_yoy_log','nominal_gdp_ytd_yoy_log','real_gdp_ytd_yoy_pct','real_gdp_ytd_yoy_log','implicit_YTD_price_log_growth']].copy()
    targets.index=pd.PeriodIndex(targets.index,freq='Q')
    for key in targets:
        s=targets[key].dropna()
        rows.append(dict(diagnostic_type='TARGET_DISTRIBUTION_LATEST_REVISED',indicator=key,N=len(s),mean=s.mean(),std=s.std(ddof=1),
            minimum=s.min(),maximum=s.max(),autocorrelation_L1=targets[key].autocorr(1),autocorrelation_L4=targets[key].autocorr(4),
            target_period_definition='standalone' if key=='nominal_gdp_yoy_log' else 'cumulative YTD'))
    for left in targets:
        for right in targets:
            pair=targets[[left,right]].dropna() if left!=right else targets[[left]].dropna()
            rows.append(dict(diagnostic_type='TARGET_PAIR_CORRELATION_LATEST_REVISED',indicator=left,other_target=right,N=len(pair),
                correlation=pair[left].corr(pair[right]) if left!=right else 1.,evidence_class='DESCRIPTIVE; TARGET PERIOD DEFINITIONS MAY DIFFER'))
    features=panel[list(FIELDS)].copy()
    mapping={'cpi':'cpi_headline_mom_log','retail':'retail_yoy_log','wholesale':'wholesale_yoy_log','exports':'exports_total_yoy_log','imports':'imports_total_yoy_log'}
    for key,field in mapping.items():features[key]=dataset.monthly[field].reindex(features.index)
    full=dataset.monthly.reindex(pd.date_range(dataset.monthly.index.min(),dataset.monthly.index.max(),freq='ME'))
    features['CPI_yoy_log']=full.cpi_headline_mom_log.rolling(12,min_periods=12).sum().reindex(features.index)
    features['PPI_yoy_log']=full.ppi_mom_log.rolling(12,min_periods=12).sum().reindex(features.index)
    quarterly=features.groupby(features.index.to_period('Q')).mean()
    counts=features.groupby(features.index.to_period('Q')).count();quarterly=quarterly.where(counts.eq(3))
    dates=pd.DatetimeIndex(pd.to_datetime(factors.date))
    qfactor=pd.Series(factors.factor.to_numpy(),index=dates).groupby(dates.to_period('Q')).mean()
    quarterly['accepted_filtered_factor']=qfactor
    for key in quarterly:
        joined=targets.join(quarterly[key]).dropna(subset=[key])
        r=dict(diagnostic_type='EX_POST_QUARTERLY_ASSOCIATION',indicator=key,
            in_accepted_DFM=key in FIELDS,loading_status='SEE_FACTOR_LOADINGS.csv' if key in FIELDS else 'NO_DFM_LOADING_NOT_IN_FACTOR_PANEL',
            aggregation='quarter mean of three observed months; no fill',evidence_class='REVISED_HISTORY_DESCRIPTIVE_NOT_CAUSAL')
        for target in targets:
            pair=joined[[key,target]].dropna()
            r['correlation_with_'+target]=pair[key].corr(pair[target]) if len(pair)>2 else np.nan
            r['N_'+target]=len(pair)
        rows.append(r)
    for name,fields in [('REAL_ONLY',['real_gdp_ytd_yoy_log']),('PRICE_ONLY',['implicit_YTD_price_log_growth']),('BOTH',['real_gdp_ytd_yoy_log','implicit_YTD_price_log_growth'])]:
        data=targets.join(qfactor.rename('factor')).dropna(subset=fields+['factor'])
        x=np.column_stack([np.ones(len(data)),data[fields].to_numpy()]);y=data.factor.to_numpy()
        beta=np.linalg.lstsq(x,y,rcond=None)[0];error=y-x@beta
        r2=1-float(sum(error**2)/sum((y-y.mean())**2))
        rows.append(dict(diagnostic_type='EX_POST_FACTOR_COMPONENT_ASSOCIATION',indicator=name,N=len(data),R2=r2,
            regressors=json.dumps(fields),evidence_class='DESCRIPTIVE_LATEST_REVISED_GDP_WITH_ACCEPTED_FILTERED_FACTOR; NOT FORECAST ACCURACY OR CAUSAL IDENTIFICATION'))
    return pd.DataFrame(rows)
