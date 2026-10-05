"""Admit POS coverage extensions only with reviewed, archived official-table evidence."""
import ast
from urllib.parse import urlparse
import pandas as pd
import numpy as np
from scripts.operations.state import read,sha


def reviewed_pos(root,row,asof):
    """Optional data review, never a new source, proxy, or transformation.

    Each approved asset supplies explicitly reviewed monthly YTD table extracts.
    A checksum-matched HTTP receipt and separate scope/value confirmations are
    mandatory. This file is never manufactured by the updater.
    """
    path=root/'config/operations_pos_scope_review.json'
    if not path.exists():return None
    review=read(path);rows=[]
    for asset in review['approved_assets']:
        if asset.get('scope_verified') is not True or asset.get('values_verified') is not True:
            raise ValueError('POS scope/value review not verified')
        if not asset.get('definition_evidence') or not asset.get('reviewer'):
            raise ValueError('POS definition evidence/reviewer missing')
        receipt_path=(root/asset['receipt_file']).resolve()
        if not receipt_path.is_relative_to((root/'data/raw').resolve()):raise ValueError('POS receipt must be an archived source receipt')
        receipt=read(receipt_path);source=(root/receipt['raw_file_path']).resolve()
        if not source.is_relative_to((root/'data/raw').resolve()) or sha(source)!=asset['checksum'] or receipt['checksum']!=asset['checksum']:
            raise ValueError('POS review source checksum mismatch')
        if receipt['http_status']!=200 or urlparse(receipt['source_url']).hostname!='cbu.uz':raise ValueError('POS review source is not successful official CBU retrieval')
        if asset['unit']!=row['raw_unit'] or asset['unit']!='million UZS':raise ValueError('POS review unit mismatch')
        if pd.Timestamp(receipt['retrieved_at'])>asof:raise ValueError('Future POS review retrieval')
        for observation in asset['observations']:
            if not observation.get('extracted_excerpt') or observation.get('value_verified') is not True:
                raise ValueError('POS table extraction evidence missing')
            period=pd.Period(observation['period'],'M')
            rows.append(dict(variable_key='pos_turnover',reference_period=str(period),reference_date=period.to_timestamp('M'),
                frequency='M',raw_value=float(observation['raw_ytd']),unit=asset['unit'],raw_unit=asset['unit'],
                flow_type='nominal_ytd',raw_file_path=receipt['raw_file_path'],checksum=receipt['checksum'],
                source_url=receipt['source_url'],retrieved_at=receipt['retrieved_at'],vintage_date=receipt['retrieved_at'],
                source_release_date=receipt.get('source_release_date'),source_release_basis='Observed source update only; not first release',
                provider=row['provider'],source_id=row['native_indicator_dataset_id'],scope_verified=True,
                parser_version='reviewed-official-POS-table-extract',schema_fingerprint=asset['checksum'],
                revision_status='reviewed_official_source_vintage',transformation=row['required_transformation'],
                clean_model_field=row['clean_model_field'],quality_flag='',is_preliminary=None))
    frame=pd.DataFrame(rows).sort_values('reference_period')
    if frame.reference_period.duplicated().any():raise ValueError('Ambiguous reviewed POS periods')
    # Execute the existing pure transformation verbatim, without running the old research builder.
    source_path=root/'scripts/research/phase6a2/build.py'
    node=next(n for n in ast.parse(source_path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='safe_flows')
    namespace={'pd':pd,'np':np}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source_path),'exec'),namespace)
    flow,yoy,_,decisions=namespace['safe_flows'](frame)
    index=pd.PeriodIndex(frame.reference_period,freq='M')
    frame['monthly_flow']=flow.reindex(index).to_numpy();frame['clean_value']=yoy.reindex(index).to_numpy()
    frame.loc[frame.clean_value.isna(),'quality_flag']='missing_growth_input;reviewed_same_vintage_POS'
    return frame
