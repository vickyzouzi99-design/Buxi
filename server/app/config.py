"""Load .env as data; never evaluate shell expressions or overwrite real env."""
import os
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[2]

def load_env():
    file=PROJECT_ROOT/".env"
    if not file.exists(): return
    for line in file.read_text(encoding="utf-8-sig").splitlines():
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key,value=line.split("=",1)
        key=key.strip();value=value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in ("'",'"'):
            value=value[1:-1]
        if key and key.replace("_","").isalnum():
            os.environ.setdefault(key,value)
