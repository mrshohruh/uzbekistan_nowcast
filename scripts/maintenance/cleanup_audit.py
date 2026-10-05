"""Phase 6E.0 audit. No existing project file is changed by this command."""
from __future__ import annotations
import ast
import csv
from collections import defaultdict,deque
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/cleanup'
EXCLUDED={'.git','.venv','venv'}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def files(root=ROOT):
    result=[]
    for base,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d not in EXCLUDED and not (Path(base)/d).is_symlink()]
        for name in names:
            p=Path(base)/name
            if not p.is_symlink():result.append(p)
    return sorted(result)


def temporary(rel):
    return any(p in {'.tmp','.phase5d_test_tmp','_pytest_temp','_pytest','test_workspace','_vendor'}
               or p.startswith('test_tmp') or re.fullmatch(r't_[0-9a-f]{8}',p) for p in Path(rel).parts)


def cache(rel):
    p=Path(rel)
    return any(x in {'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','htmlcov','.ipynb_checkpoints'}
               or x.startswith('pytest-cache-files-') for x in p.parts) or p.suffix in {'.pyc','.pyo'} or p.name in {'.coverage','Thumbs.db','.DS_Store'}


def write(name,rows,columns=None):
    cols=columns or (list(rows[0]) if rows else [])
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)


def json_out(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',check=True).stdout


def audit():
    OUT.mkdir(parents=True,exist_ok=True)
    status=git('status','--porcelain=v1','-uall')
    branch=git('branch','--show-current').strip();commit=git('rev-parse','HEAD').strip()
    (OUT/'pre_cleanup_git_status.txt').write_text(f'branch: {branch}\nHEAD: {commit}\n{status}',encoding='utf-8')
    tracked=set(git('ls-files').splitlines())
    dirty={line[3:].split(' -> ')[-1] for line in status.splitlines() if line[:2]!='??'}
    all_files=[p for p in files() if not p.is_relative_to(OUT) and not p.is_relative_to(ROOT/'archive')]
    paths={p.relative_to(ROOT).as_posix():p for p in all_files}
    protected=set()
    protected.update(r for r in paths if r.startswith(('results/phase6d/','scripts/research/phase6d/')))
    frozen=ROOT/'results/phase6d/phase6d_protected_start.json'
    if frozen.exists():protected.update(json.loads(frozen.read_text(encoding='utf-8')))
    protected.update(r for r in paths if r.startswith(('results/phase6d/','scripts/research/phase6d/','results/production/',
        'dashboard/current/','data/','metadata/','config/','registry/','src/','tests/')) and not temporary(r))
    protected.add('dashboard/phase6d_shadow_monitor.html')
    bundle=json.loads((ROOT/'results/phase6d/phase6d_frozen_challengers.json').read_text())
    for key in ['code_hashes','source_artifact_hashes','static_specification_hashes']:protected.update(bundle[key])
    # Paths named by current manifest hashes remain fixed even if a directory looks temporary.
    manifest=json.loads((ROOT/'results/phase6d/phase6d_run_manifest.json').read_text())
    protected.update(manifest.get('read_only_input_hashes',{}))
    protected.update(dirty & paths.keys())
    python={r for r in paths if r.endswith('.py')}
    core={r for r in python if not temporary(r) and not cache(r)}
    modules={}
    for r in core:
        if r.startswith('src/'):
            m=r[4:-3].replace('/','.')
            modules[m.removesuffix('.__init__')]=r
    graph=defaultdict(set);imported=defaultdict(set);referenced=defaultdict(set);errors={}
    edges=[]
    for r in core:
        try:
            text=paths[r].read_text(encoding='utf-8-sig');tree=ast.parse(text,filename=r)
        except (UnicodeError,SyntaxError) as exc:
            errors[r]=str(exc);continue
        names=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):names.extend(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):
                base=n.module or ''
                if n.level:
                    package=r.removeprefix('src/').removesuffix('.py').replace('/','.')
                    package=package.removesuffix('.__init__') if r.endswith('/__init__.py') else package.rsplit('.',1)[0]
                    bits=package.split('.')
                    base='.'.join(bits[:len(bits)-n.level+1]+([base] if base else []))
                names.append(base);names.extend(base+'.'+a.name for a in n.names)
            elif isinstance(n,ast.Constant) and isinstance(n.value,str):
                value=n.value.replace('\\','/')
                if value.endswith('.py'):
                    possible=[value,(Path(r).parent/value).as_posix()]
                    for target in possible:
                        if target in core:
                            graph[r].add(target);referenced[target].add(r);edges.append(dict(source=r,target=target,kind='DYNAMIC_OR_PATH'))
        for name in names:
            target=modules.get(name)
            local=(Path(r).parent/(name.replace('.','/')+'.py')).as_posix()
            candidates=[target] if target else [local] if local in core else []
            if not candidates and '.' not in name:
                candidates=[x for x in core if Path(x).stem==name and x.startswith('scripts/research/')]
            for t in candidates:
                graph[r].add(t);imported[t].add(r);edges.append(dict(source=r,target=t,kind='IMPORT'))
                if t.startswith('src/'):
                    parent=Path(t).parent
                    while str(parent)!='src':
                        init=(parent/'__init__.py').as_posix()
                        if init in core:graph[r].add(init)
                        parent=parent.parent
    # Exact references supplement AST imports, including shell/config/documentation invocations.
    texts={}
    for r,p in paths.items():
        if temporary(r) or cache(r) or p.stat().st_size>4_000_000:continue
        if p.suffix.lower() in {'.py','.md','.txt','.json','.yaml','.yml','.toml','.ps1','.bat','.sh','.csv'}:
            try:texts[r]=p.read_text(encoding='utf-8-sig').replace('\\','/')
            except UnicodeError:pass
    operational_refs=set()
    for source,text in texts.items():
        for target in core:
            if source!=target and (target in text or ('/'+Path(target).name in text and str(Path(target).parent) in text)):
                referenced[target].add(source)
                if source in core:graph[source].add(target)
                if source.startswith(('config/','docs/')) or source in ['README.md','PROJECT_STATE.md','PROJECT_SPEC.md'] or Path(source).suffix in {'.ps1','.bat','.sh'}:
                    operational_refs.add(target)
    production_roots={r for r in core if r.startswith('src/uznowcast/operational/')}
    pipeline_roots={r for r in core if r in ['src/uznowcast/cli.py','src/uznowcast/pipeline.py'] or (r.startswith('scripts/') and '/research/' not in r)}
    shadow_roots={r for r in core if r.startswith('scripts/research/phase6d/')}
    reconstruction_roots=set(bundle['code_hashes']) & core
    test_roots={r for r in core if r.startswith('tests/') or Path(r).name.startswith('test_')}
    def closure(roots):
        found=set(roots);todo=deque(roots)
        while todo:
            for target in graph[todo.popleft()]-found:found.add(target);todo.append(target)
        return found
    prod=closure(production_roots);pipeline=closure(pipeline_roots);shadow=closure(shadow_roots)
    reconstruction=closure(reconstruction_roots);testing=closure(test_roots);documentation=closure(operational_refs)
    active=prod|pipeline|shadow|reconstruction|testing|documentation
    protected.update(active)
    inventory=[];pyrows=[];data=[];results=[];plan=[]
    groups=defaultdict(list)
    protected_hashes={}
    unreadable=[];hashes={}
    def hash_or_unknown(path):
        try:return sha(path)
        except PermissionError:return 'UNREADABLE'
    # Independent local reads overlap Windows filesystem latency. No mutation,
    # child agent, network access, or import execution is involved.
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures={executor.submit(hash_or_unknown,p):r for r,p in paths.items()}
        for i,future in enumerate(as_completed(futures),1):
            r=futures[future];hashes[r]=future.result()
            if i%1000==0:print(f'Audit checksums {i}/{len(paths)}',flush=True)
    for i,(r,p) in enumerate(paths.items()):
        st=p.stat();is_temp=temporary(r);is_cache=cache(r)
        h=hashes[r]
        if h=='UNREADABLE':unreadable.append(r)
        protection=r in protected
        category='CURRENT_ACTIVE' if protection else 'TEMPORARY' if is_temp or is_cache else 'CURRENT_REFERENCE' if r in referenced else 'HISTORICAL_ARCHIVE' if r.startswith(('results/','dashboard/','docs/')) else 'UNKNOWN'
        action='KEEP';destination='';reason='Protected hash/path, current input, active import, or pre-existing user change' if protection else 'Unknown dependency: keep path stable'
        if not protection and is_cache and r not in dirty:
            action='DELETE_SAFE';reason='Regenerable cache; outside all protected paths'
        elif not protection and is_temp and r not in dirty:
            action='ARCHIVE';destination='archive/historical_results/'+r;reason='Disposable old test workspace; preserve its contents including source copies until verification'
        elif not protection and category in ['HISTORICAL_ARCHIVE','UNKNOWN']:
            action='REVIEW';reason='Not enough evidence to move an existing semantic path safely'
        if h=='UNREADABLE':
            action='REVIEW';destination='';reason='Unreadable existing file: preserve and flag for manual review'
        if protection:protected_hashes[r]=h
        refs=sorted(imported[r]|referenced[r])
        inventory.append(dict(path=r,size_bytes=st.st_size,sha256=h,category=category,git_tracked=r in tracked,
            user_modified=r in dirty,last_modified=datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat(),protected=protection))
        plan.append(dict(path=r,size_bytes=st.st_size,category=category,action=action,destination=destination,
            confidence='HIGH' if action in ['KEEP','ARCHIVE','DELETE_SAFE'] else 'REVIEW',reason=reason,referenced_by=';'.join(refs),hash=h,protected=protection))
        if h!='UNREADABLE':groups[(h,st.st_size)].append(r)
        if r in python:
            classification='ACTIVE_TEST' if r in test_roots else 'ACTIVE_DIRECT' if r in shadow_roots|production_roots else 'ACTIVE_DATA_PIPELINE' if r in pipeline else 'ACTIVE_DEPENDENCY' if r in active else 'ACTIVE_REPRODUCIBILITY' if protection else 'LEGACY_REFERENCED' if refs else 'UNKNOWN'
            pyrows.append(dict(path=r,classification=classification,imported_by=';'.join(sorted(imported[r])),referenced_by=';'.join(sorted(referenced[r])),
                entrypoint_reachable=r in prod|pipeline|shadow|reconstruction,test_reachable=r in testing,phase6d_required=r in shadow,
                production_required=r in prod,reproducibility_required=r in reconstruction or protection,git_tracked=r in tracked,
                last_modified=inventory[-1]['last_modified'],candidate_action=action,reason=reason))
        if r.startswith(('data/','metadata/')) and not is_temp:
            data.append(dict(path=r,classification='ACTIVE_RAW_SOURCE' if r.startswith('data/raw/') else 'ACTIVE_PROVENANCE' if r.startswith('metadata/') else 'ACTIVE_MODEL_INPUT' if r.startswith('data/master/') else 'UNKNOWN_DATA',action='KEEP',reason='Preserve official provenance and reconstruction inputs',sha256=h))
        if r.startswith('results/'):
            results.append(dict(path=r,classification='CURRENT_ACTIVE' if r.startswith(('results/production/','results/phase6d/')) else 'REPRODUCIBILITY_REQUIRED' if protection else 'TEMPORARY' if is_temp or is_cache else 'HISTORICAL_ARCHIVE',action=action,reason=reason,sha256=h))
    dup=[];actions={r['path']:r['action'] for r in plan}
    for (h,size),members in groups.items():
        if len(members)<2:continue
        ordered=sorted(members,key=lambda p:(p not in protected,temporary(p),cache(p),p))
        for member in ordered[1:]:
            dup.append(dict(sha256=h,size=size,canonical_file=ordered[0],duplicate_file=member,
                action=actions[member],reason='Semantic/provenance paths retained; only independently approved cache/temp actions apply'))
    write('repository_inventory.csv',inventory);write('active_python_inventory.csv',pyrows)
    write('data_inventory.csv',data);write('result_artifact_inventory.csv',results);write('duplicate_files.csv',dup)
    write('cleanup_plan.csv',plan);write('dependency_edges.csv',edges,['source','target','kind'])
    write('test_inventory.csv',[dict(path=r,classification='CURRENT_GOVERNANCE' if 'shadow' in r or 'phase6' in r else 'CURRENT_MODEL' if '/models/' in r else 'CURRENT_REGRESSION',action='KEEP',reason='Existing protective behavior retained') for r in sorted(test_roots)])
    json_out('protected_hashes_before.json',protected_hashes)
    json_out('audit_summary.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),git_commit=commit,git_branch=branch,
        scope='Project files excluding .git, .venv, archive, and newly generated cleanup audit output; installed environment untouched',
        files_before=len(paths),bytes_before=sum(x['size_bytes'] for x in inventory),directories_before=len({str(p.parent) for p in all_files}),
        python_files_before=len(python),active_python_files=len(active),cache_temp_files=sum(temporary(r) or cache(r) for r in paths),
        actions={a:sum(r['action']==a for r in plan) for a in ['KEEP','ARCHIVE','DELETE_SAFE','REVIEW']},
        protected_files=len(protected_hashes),parse_errors=errors,unreadable_files=unreadable,production_entrypoints=sorted(production_roots),
        pipeline_entrypoints=sorted(pipeline_roots),phase6d_entrypoints=sorted(shadow_roots),
        pre_existing_deleted_paths=sorted(dirty-set(paths)),user_modified_existing=sorted(dirty&paths.keys())))
    if any(r['category']=='CURRENT_ACTIVE' and r['action'] in ['ARCHIVE','DELETE_SAFE'] for r in plan):raise RuntimeError('Unsafe current-active cleanup plan')
    print(json.dumps(json.loads((OUT/'audit_summary.json').read_text()),indent=2),flush=True)


if __name__=='__main__':audit()
