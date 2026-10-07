"""Reproduce current science and record the actual loaded repository modules."""
from pathlib import Path
import json,sys
from scripts.production.run import build,ROOT
OUT=ROOT/'results/repository_cleanup/phase6h1'
if __name__=='__main__':
    current=build(out=OUT/'deterministic',publish=False)
    modules=sorted({Path(m.__file__).resolve().relative_to(ROOT).as_posix() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(ROOT) and '.venv' not in Path(m.__file__).parts})
    (OUT/'runtime_trace.json').write_text(json.dumps(dict(current=current,loaded_modules=modules),indent=2)+'\n',encoding='utf-8')
