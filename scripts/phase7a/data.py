"""Strict research transformations and source-definition checks."""
import json
import numpy as np
import pandas as pd

def annual_siat(payload: bytes) -> pd.DataFrame:
    block=json.loads(payload)[0]
    metadata={r['name_en']:r['value_en'] for r in block['metadata']}
    if 'nnual' not in metadata['Periodicity'] or metadata['Indicator identification number (code)']!='1.02.02.0019':
        raise ValueError('Unexpected SIAT definition/frequency')
    if metadata['Unit of measurement']!='Million kWt hour':
        raise ValueError('Unexpected SIAT unit')
    rows=[r for r in block['data'] if r.get('Klassifikator_en')=='Republic of Uzbekistan']
    if len(rows)!=1: raise ValueError('National aggregate is not unique')
    return pd.DataFrame([dict(year=int(y),electricity_consumption_gwh=float(v),measurement_definition=metadata['Indicator name'],period_type='annual',source_update_date=metadata['Last modified date'],quality_flag='VINTAGE_UNVERIFIED') for y,v in rows[0].items() if str(y).isdigit() and len(str(y))==4])

def transform(frame: pd.DataFrame) -> pd.DataFrame:
    result=frame.copy()
    dates=pd.to_datetime(result.date).dt.to_period('M')
    if dates.duplicated().any(): raise ValueError('Duplicate monthly observation')
    levels=pd.Series(pd.to_numeric(result.electricity_consumption_gwh,errors='raise').to_numpy(), index=dates)
    lag=levels.reindex(dates-12).to_numpy()
    valid=(levels.to_numpy()>0)&(lag>0)
    result['electricity_yoy_log_growth']=np.nan
    result['electricity_yoy_pct_growth']=np.nan
    result.loc[valid,'electricity_yoy_log_growth']=100*np.log(levels.to_numpy()[valid]/lag[valid])
    result.loc[valid,'electricity_yoy_pct_growth']=100*(levels.to_numpy()[valid]/lag[valid]-1)
    result['transformation_valid']=valid
    result['validity_flag']=np.where(valid,'VALID','MISSING_OR_NONPOSITIVE_CURRENT_OR_YEAR_AGO')
    return result
