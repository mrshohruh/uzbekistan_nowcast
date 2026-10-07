"""Prepare or apply an exact generated-file inventory with constructor evidence."""
from pathlib import Path
import csv,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/repository_cleanup'
PLAN=OUT/'phase6h1/generated_file_plan.json'
if '--apply' not in sys.argv:
    external=set(json.loads((ROOT/'config/bootstrap_inputs.json').read_text())['files'])
    constructors={}
    for name in ['scripts/operations/run_tests.py','scripts/phase6e/tests.py']:
        constructors[name]=subprocess.check_output(['git','show','fe252655:'+name],cwd=ROOT,text=True)
    targets=[]
    for parent,pattern,proof in [
        ('results/op_tests','o_*','scripts/operations/run_tests.py creates disposable pytest roots o_UUID'),
        ('results/phase6e','t_*','scripts/phase6e/tests.py creates disposable pytest roots t_UUID'),
        ('results/phase6d','t_*','Historical pytest workspace; nested test functions and fixture outputs'),
        ('results/phase6c','t_*','Historical pytest workspace; nested test functions and fixture outputs'),
        ('results/phase6c','test_workspace_*','Historical pytest collection workspaces'),
        ('results/phase6c','pytest-cache-files-*','pytest cache'),
        ('data/t','*','Current validate_current temporary test roots')]:
        for p in (ROOT/parent).glob(pattern):
            if p.is_dir():targets.append((p,proof))
    for rel,proof in [
        ('results/phase6e/tests','Historical pytest reports; constructor saved in audit'),
        ('results/phase6e/browser_profile','Chromium temporary screenshot profile; Last Version/Crashpad cache markers'),
        ('results/phase6e/rerun','Deterministic rerun artifacts; compare scientific files with old_baseline'),
        ('results/phase6c/repository_test_tmp','Historical pytest workspace'),
        ('results/phase6f/test_tmp','Historical pytest workspace'),
        ('results/phase6g5/pytest_tmp_final','Historical pytest workspace'),
        ('results/reconciliation/validation_workspaces','Historical pytest collection workspaces'),
        ('results/research/phase6b2/test_tmp_models','Historical pytest models workspace')]:
        p=ROOT/rel
        if p.exists():targets.append((p,proof))
    entries=[]
    for p,proof in targets:
        rel=p.relative_to(ROOT).as_posix()
        if any(x==rel or x.startswith(rel+'/') for x in external):raise ValueError('Evidence intersects cleanup: '+rel)
        for parent,dirs,files in os.walk(p):
            for n in files:
                f=Path(parent)/n
                entries.append(dict(path=f.relative_to(ROOT).as_posix(),size=f.stat().st_size,mtime_ns=f.stat().st_mtime_ns,proof=proof,target=rel))
    # Rerun numerical artifacts must have another independently preserved copy.
    import hashlib
    checks=[]
    for p in (ROOT/'results/phase6e/rerun').glob('*'):
        if p.suffix not in {'.csv','.json','.html'} or p.name in {'phase6e_run_manifest.json','phase6e_production_policy.json'}:continue
        other=ROOT/'results/repository_cleanup/phase6h1/old_baseline'/p.name
        if not other.exists() and p.name=='uzbekistan_nowcast_v2.html':other=ROOT/'results/repository_cleanup/phase6h1/old_baseline'/p.name
        equal=other.exists() and p.read_bytes()==other.read_bytes()
        checks.append(dict(file=str(p.relative_to(ROOT)),preserved_copy=str(other.relative_to(ROOT)),equal=equal))
        if not equal:raise ValueError('Unproven rerun artifact: '+str(p))
    PLAN.write_text(json.dumps(dict(constructors=constructors,rerun_checks=checks,targets=[dict(path=p.relative_to(ROOT).as_posix(),proof=proof) for p,proof in targets],files=entries),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(generated_files=len(entries),explicit_targets=len(targets),rerun_checks=len(checks))))
else:
    plan=json.loads(PLAN.read_text(encoding='utf-8'));removed=[]
    for r in plan['files']:
        p=(ROOT/r['path']).resolve();base=(ROOT/r['target']).resolve()
        if not p.is_relative_to(base) or not base.is_relative_to(ROOT.resolve()):raise ValueError('Unsafe planned file')
        if not p.exists():continue
        stat=p.stat()
        if stat.st_size!=r['size'] or stat.st_mtime_ns!=r['mtime_ns']:raise ValueError('Generated file changed after audit: '+r['path'])
        p.unlink();removed.append(dict(path=r['path'],category='G: generated/staging',reason=r['proof'],sha256='GENERATED_REPRODUCIBLE',tracked=False,recoverable_commit='constructor at fe252655; original raw data retained'))
    for r in plan['targets']:
        for parent,dirs,names in os.walk(ROOT/r['path'],topdown=False):
            try:Path(parent).rmdir()
            except OSError:pass
    manifest=OUT/'phase6h1_removed_files.csv'
    with manifest.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;old=list(reader)
    with manifest.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(old+removed)
    (OUT/'phase6h1/generated_cleanup.json').write_text(json.dumps(dict(removed_files=len(removed),targets=plan['targets']),indent=2)+'\n')
    print(json.dumps(dict(removed_files=len(removed))))
