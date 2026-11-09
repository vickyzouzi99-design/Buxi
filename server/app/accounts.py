"""Per-code private beta accounts; only hashes of codes and sessions persist."""
import hashlib,secrets,time,json,uuid
from . import vectors
from .rules import FRIENDS

def digest(value): return hashlib.sha256(value.encode()).hexdigest()

class Accounts:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS invites(hash TEXT PRIMARY KEY, owner TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, owner TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(owner TEXT PRIMARY KEY, greetings INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, owner TEXT NOT NULL, friend TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, active INTEGER NOT NULL, embedding BLOB NOT NULL, model TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS dialogs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, friend TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS greetings(owner TEXT NOT NULL, friend TEXT NOT NULL, day TEXT NOT NULL, PRIMARY KEY(owner,day));
            CREATE TABLE IF NOT EXISTS knowledge(id TEXT PRIMARY KEY, content TEXT NOT NULL, embedding BLOB NOT NULL, model TEXT NOT NULL);
            """)
    def issue(self,count=1):
        codes=[]
        with self.store.connect() as db:
            for _ in range(count):
                code=secrets.token_urlsafe(18);owner=str(uuid.uuid4())
                db.execute('INSERT INTO invites VALUES (?,?)',(digest(code),owner));codes.append(code)
        return codes
    def login(self,code):
        with self.store.connect() as db:
            row=db.execute('SELECT owner FROM invites WHERE hash=?',(digest(code),)).fetchone()
            if not row: raise PermissionError('内测码无效')
            token=secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires < ?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',(digest(token),row['owner'],time.time()+86400*7))
        return token
    def owner(self,token):
        with self.store.connect() as db:
            row=db.execute('SELECT owner FROM sessions WHERE hash=? AND expires>?',(digest(token),time.time())).fetchone()
        if not row: raise PermissionError('请先输入内测码')
        return row['owner']
    def logout(self,token):
        with self.store.connect() as db: db.execute('DELETE FROM sessions WHERE hash=?',(digest(token),))
    def prefs(self,owner,value=None):
        with self.store.connect() as db:
            if value is not None: db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(owner,int(value)))
            row=db.execute('SELECT greetings FROM settings WHERE owner=?',(owner,)).fetchone()
        return {'greetings':bool(row and row[0])}
    def memories(self,owner):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,friend,content,source,active FROM memories WHERE owner=? ORDER BY created DESC',(owner,))]
    def save_memory(self,owner,friend,content,source,mid=None,active=True):
        if friend not in FRIENDS: raise ValueError('未知朋友')
        content=content.strip()
        if not content or len(content)>1000: raise ValueError('记忆需为1–1000字')
        v,name=vectors.embed(content)
        with self.store.connect() as db:
            if mid and not db.execute('SELECT id FROM memories WHERE owner=? AND id=?',(owner,mid)).fetchone(): raise KeyError()
            mid=mid or str(uuid.uuid4())
            db.execute('INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?,?,?,?,?)',(mid,owner,friend,content,source,int(active),vectors.pack(v),name,time.time()))
        return mid
    def delete_memory(self,owner,mid):
        with self.store.connect() as db: db.execute('DELETE FROM memories WHERE owner=? AND id=?',(owner,mid))
    def recall(self,owner,friend,query):
        v,name=vectors.embed(query)
        with self.store.connect() as db:
            vectors.enable(db)
            # Owner, role, active state and embedding version filter the candidate set.
            rows=db.execute('SELECT id,content,source,vec_distance_cosine(embedding,?) AS distance FROM memories WHERE owner=? AND friend=? AND active=1 AND model=? ORDER BY distance LIMIT 3',(vectors.pack(v),owner,friend,name)).fetchall()
        return [dict(r) for r in rows if r['distance'] is not None and r['distance']<0.85]
    def history(self,owner,friend):
        with self.store.connect() as db: return [dict(r) for r in db.execute('SELECT role,content FROM dialogs WHERE owner=? AND friend=? ORDER BY created,rowid',(owner,friend))]
    def exchange(self,owner,friend,user,answer):
        with self.store.connect() as db:
            for role,text in [('user',user),('assistant',answer)]: db.execute('INSERT INTO dialogs VALUES (?,?,?,?,?,?)',(str(uuid.uuid4()),owner,friend,role,text,time.time()))
    def greet(self,owner):
        if not self.prefs(owner)['greetings']: return None
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        friend=list(FRIENDS)[secrets.randbelow(len(FRIENDS))]
        with self.store.connect() as db:
            changed=db.execute('INSERT OR IGNORE INTO greetings VALUES (?,?,?)',(owner,friend,day)).rowcount
        return {'friend':friend,'content':FRIENDS[friend]['greeting']} if changed else None
    def index_knowledge(self):
        from .tarot import deck
        for card in deck():
            content=json.dumps(card,ensure_ascii=False)
            v,name=vectors.embed(card['name']+' '+card['prompt']+' '+card['meanings']['reversed'])
            with self.store.connect() as db: db.execute('INSERT OR REPLACE INTO knowledge VALUES (?,?,?,?)',(card['id'],content,vectors.pack(v),name))
    def search_knowledge(self,query):
        from .tarot import deck
        exact=[c for c in deck() if c['name']==query.strip() or c['id']==query.strip()]
        if exact: return [{'card':c,'distance':0.0} for c in exact]
        v,name=vectors.embed(query)
        with self.store.connect() as db:
            vectors.enable(db)
            rows=db.execute('SELECT content,vec_distance_cosine(embedding,?) AS distance FROM knowledge WHERE model=? ORDER BY distance LIMIT 5',(vectors.pack(v),name)).fetchall()
        return [dict(card=json.loads(r['content']),distance=r['distance']) for r in rows if r['distance'] is not None and r['distance']<.95]
