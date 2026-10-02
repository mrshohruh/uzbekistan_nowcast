"""Finalize verified research evidence without changing historical artifacts."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from run import ROOT,OUT,DOC,protect,sha,js


def main():
    after=protect()
    required=['results.md','run_manifest.json','gdp_release_audit.csv','leak_reproduction.csv','leak_reproduction.json',
              'benchmark_gdp_information_audit.csv','forecasts.csv','matched_forecasts.csv','horizon_metrics.csv',
              'model_metrics.csv','combination_metrics.csv','prediction_revision_audit.csv','origin_information_audit.csv',
              'failed_origins.csv','test_results.xml','protected_before.json','protected_after.json']
    for name in required:
        assert (OUT/('phase6b1_'+name)).is_file(),name
    suite=ET.parse(OUT/'phase6b1_test_results.xml').getroot().find('testsuite')
    tests={key:int(suite.attrib[key]) for key in ['tests','errors','failures','skipped']}
    assert tests['errors']==tests['failures']==tests['skipped']==0,tests
    sources=pd.read_csv(OUT/'phase6b1_GDP_source_evidence.csv')
    for row in sources.itertuples():
        assert sha(ROOT/row.path)==row.sha256,row.path
    training=pd.read_csv(OUT/'phase6b1_bridge_training_information_audit.csv')
    assert pd.to_datetime(training.dependent_GDP_available_date).le(pd.to_datetime(training.forecast_origin_date)).all()
    lag=training.dropna(subset=['lag_GDP_available_date'])
    assert pd.to_datetime(lag.lag_GDP_available_date).le(pd.to_datetime(lag.forecast_origin_date)).all()
    assert training.training_quarter.ne(training.target_quarter).all()
    forecasts=pd.read_csv(OUT/'phase6b1_forecasts.csv')
    assert not forecasts.duplicated(['model','target_quarter','horizon','lag_mode']).any()
    b=forecasts.loc[forecasts.model.eq('DFM_DOMESTIC_3__BRIDGE_B_CLEAN')]
    assert b.loc[b.horizon.eq('H1'),'prediction'].isna().all()
    assert b.prediction.notna().sum()==40
    reference=json.loads((OUT/'phase6b1_determinism_reference.json').read_text())
    current={name:sha(OUT/name) for name in reference}
    assert reference==current,'Numeric rerun mismatch'
    js('determinism_check',dict(numeric_tables_checked=len(reference),byte_identical=True,before=reference,after=current))
    manifest=json.loads((OUT/'phase6b1_run_manifest.json').read_text())
    manifest['status']='COMPLETED_RESEARCH_ONLY'
    manifest['test_results']=tests
    manifest['determinism_verification']=dict(numeric_tables_checked=len(reference),byte_identical=True)
    manifest['model_forecast_counts_by_horizon']=forecasts.groupby(['model','lag_mode','horizon']).prediction.count().rename('count').reset_index().to_dict('records')
    manifest['failed_origins_by_model_horizon']=forecasts.loc[forecasts.prediction.isna()].groupby(['model','horizon']).size().rename('count').reset_index().to_dict('records')
    manifest['affected_Bridge_B_quarters']=sorted(b.loc[b.prediction.isna(),'target_quarter'].unique().tolist())
    manifest['protected_artifact_hashes']=after
    manifest['code_hashes']={p.name:sha(p) for p in (ROOT/'scripts/research/phase6b1').glob('*.py')}
    verification=f"\n\nFinal verification: **{tests['tests']} tests passed**, zero failures/errors/skips. **{len(reference)} core numeric outputs are byte-identical across reruns**. **{len(after)} protected artifacts are byte-identical**, including every inventoried Phase 6B artifact. Stored GDP source inspection checksums also match. No promotion or dashboard replacement.\n"
    for path in [OUT/'phase6b1_results.md',DOC/'phase6b1_gdp_information_boundary_report.md']:
        content=path.read_text(encoding='utf-8').split('\n\nFinal verification:')[0]
        path.write_text(content+verification,encoding='utf-8')
    js('protected_after',after)
    manifest['output_hashes']={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in
                             ['phase6b1_run_manifest.json','phase6b1_pipeline.log']}
    manifest['report_sha256']=sha(DOC/'phase6b1_gdp_information_boundary_report.md')
    js('run_manifest',manifest)
    protect()


if __name__=='__main__':
    main()
