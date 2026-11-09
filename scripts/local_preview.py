"""Single supported API, also in local mode. No alternate unauthenticated adapter."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
if __name__=='__main__':
    import uvicorn
    uvicorn.run('server.app.main:app',host='127.0.0.1',port=8080)
