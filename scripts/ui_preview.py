"""Isolated UI acceptance server. No production account or database is used."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
os.environ['BUXI_DATA_DIR']=str(ROOT/'data/ui-acceptance')
os.environ['BUXI_ALLOWED_ORIGINS']='http://127.0.0.1:8081,http://localhost:8081'
from server.app.config import load_env
load_env()
from server.app.service import Store
from server.app.accounts import Accounts,digest
import uvicorn

if __name__=='__main__':
 store=Store();accounts=Accounts(store)
 with store.connect() as db:db.execute('INSERT OR IGNORE INTO invites VALUES (?,?)',(digest('buxi-local-ui-acceptance'),'ui-acceptance-only'))
 uvicorn.run('server.app.main:app',host='127.0.0.1',port=8081)
