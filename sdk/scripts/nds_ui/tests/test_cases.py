#!/usr/bin/env python3
"""The nds_ui case set (without the refuse=1 rows of cases_refuse.py) is pinned.
History: 00345a01... = MOD037's own proof set (work/mod037_nds/verification.json); the C-port
tick-wrap and isolated-flag cases (2026-10-19) extended it to 45d6ecea... (pinned 2026-10-20,
the set in use since the C port); refusal rows (MOD042) are appended separately."""
import gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from nds_ui import tests,cases
PINNED='45d6eceaccc24c19b89e56604273816c70698b18e9d9336b567b964044f1dd55'
def main():
    d,key,sec,regen=tests.load_cases();d=dict(cases=[c for c in d['cases'] if not c.get('refuse')],formats=d['formats']);h=hashlib.sha256((json.dumps(d,indent=1)+'\n').encode()).hexdigest()
    tags={}
    for c in d['cases']:
        for t in cases.tag(c):tags[t]=tags.get(t,0)+1
    print(json.dumps(dict(status='pass' if h==PINNED else 'fail',sha256=h,cases=len(d['cases']),formats=len(d['formats']),cases_per_module=tags,seconds=sec,regenerated=regen),indent=1))
    return 0 if h==PINNED else 1
if __name__=='__main__':sys.exit(main())
