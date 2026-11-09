"""Local operator CLI. Invite codes are credentials: distribute one per person."""
import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.app.config import load_env
load_env()
from server.app.service import Store
from server.app.accounts import Accounts,digest
p=argparse.ArgumentParser();p.add_argument('--create-codes',type=int);p.add_argument('--import-local',action='store_true');p.add_argument('--reindex',action='store_true');a=p.parse_args()
s=Store();accounts=Accounts(s)
if a.create_codes:
    if not 1<=a.create_codes<=100: p.error('数量需要1–100')
    for code in accounts.issue(a.create_codes): print(code)
if a.import_local:
    import getpass
    code=getpass.getpass('Owner invite code: ')
    with s.connect() as db:
        row=db.execute('SELECT owner FROM invites WHERE hash=?',(digest(code),)).fetchone()
        if not row: p.error('Invalid invite code')
        db.execute("UPDATE results SET owner_id=? WHERE owner_id='local'",(row['owner'],))
    print('Local records transferred to the selected private account.')

if a.reindex:
    accounts.index_knowledge()
    with s.connect() as db: rows=db.execute('SELECT * FROM memories').fetchall()
    for row in rows: accounts.save_memory(row['owner'],row['friend'],row['content'],row['source'],row['id'],bool(row['active']))
    print('Public knowledge and existing authorized memories reindexed.')
