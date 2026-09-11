"""Isolated one-frame comparison; never rewrites production settings or the master."""
from pathlib import Path
import sys,runpy,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import render_contract
args=sys.argv[sys.argv.index('--')+1:]
choice=args[0]
job=args[1] if len(args)>1 else 'drive'
assert job in ('drive','route')
assert choice in ('64x16','128x8','64x8')
base=render_contract.load_config(ROOT)
cfg={**base,'samples':128 if choice=='128x8' else 64,'color_depth':16 if choice=='64x16' else 8,'run_name':'compare-'+choice}
render_contract.load_config=lambda root:cfg
sys.argv=['render.py','--','sample','desktop',job]
runpy.run_path(str(ROOT/'scripts/render.py'),run_name='__main__')


