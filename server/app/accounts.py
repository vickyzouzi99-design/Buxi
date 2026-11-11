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
            columns={r[1] for r in db.execute('PRAGMA table_info(dialogs)')}
            if 'conversation_id' not in columns:
                db.execute('ALTER TABLE dialogs ADD COLUMN conversation_id TEXT')
            if 'metadata' not in columns:
                db.execute("ALTER TABLE dialogs ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'")
            for owner,friend in db.execute('SELECT DISTINCT owner,friend FROM dialogs WHERE conversation_id IS NULL').fetchall():
                cid=str(uuid.uuid4())
                db.execute("INSERT OR IGNORE INTO conversations VALUES (?,?,?,?,?,'active',?,?)",(cid,owner,friend,None,'daily',time.time(),time.time()))
                cid=db.execute("SELECT id FROM conversations WHERE owner=? AND friend=? AND reading_key='daily'",(owner,friend)).fetchone()[0]
                db.execute('UPDATE dialogs SET conversation_id=? WHERE owner=? AND friend=? AND conversation_id IS NULL',(cid,owner,friend))
            db.execute('PRAGMA user_version=3')
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
            db.execute('BEGIN IMMEDIATE')
            if mid and not db.execute('SELECT id FROM memories WHERE owner=? AND id=?',(owner,mid)).fetchone(): raise KeyError()
            old=db.execute('SELECT friend FROM memories WHERE owner=? AND id=?',(owner,mid)).fetchone() if mid else None
            self.invalidate_context(db,owner,friend)
            if old and old[0]!=friend: self.invalidate_context(db,owner,old[0])
            mid=mid or str(uuid.uuid4())
            db.execute('INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?,?,?,?,?)',(mid,owner,friend,content,source,int(active),vectors.pack(v),name,time.time()))
        return mid
    def delete_memory(self,owner,mid):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT friend FROM memories WHERE owner=? AND id=?',(owner,mid)).fetchone()
            if row: self.invalidate_context(db,owner,row[0])
            db.execute('DELETE FROM memories WHERE owner=? AND id=?',(owner,mid))

    def invalidate_context(self,db,owner,friend):
        # Prior replies may paraphrase a memory. Keep history for display but exclude it
        # from subsequent prompts. No summaries or cached operation replies can re-inject it.
        db.execute('UPDATE conversations SET context_after=? WHERE owner=? AND friend=?',(time.time(),owner,friend))
        redacted=json.dumps({'role':'assistant','content':'记忆已更新，旧回复不再重放；可查看已有记录或继续聊天。','replay_redacted':True},ensure_ascii=False)
        db.execute("UPDATE operations SET response=? WHERE owner=? AND scope IN (SELECT 'chat:'||id FROM conversations WHERE owner=? AND friend=?) AND state='done'",(redacted,owner,owner,friend))
    def recall(self,owner,friend,query):
        v,name=vectors.embed(query)
        with self.store.connect() as db:
            vectors.enable(db)
            # Owner, role, active state and embedding version filter the candidate set.
            rows=db.execute('SELECT id,content,source,vec_distance_cosine(embedding,?) AS distance FROM memories WHERE owner=? AND friend=? AND active=1 AND model=? ORDER BY distance LIMIT 3',(vectors.pack(v),owner,friend,name)).fetchall()
        return [dict(r) for r in rows if r['distance'] is not None and r['distance']<0.85]
    def history(self,owner,friend,conversation_id=None,context=False):
        with self.store.connect() as db:
            args=[owner,friend];where='owner=? AND friend=?'
            if conversation_id:
                c=self.conversation(owner,friend,conversation_id)
                where+=' AND conversation_id=?';args.append(conversation_id)
                if context: where+=' AND created>?';args.append(c['context_after'])
            rows=db.execute('SELECT role,content,metadata,conversation_id FROM dialogs WHERE '+where+' ORDER BY created,rowid',args).fetchall()
            return [dict(role=r['role'],content=r['content'],conversation_id=r['conversation_id'],**json.loads(r['metadata'])) for r in rows]
    def exchange(self,owner,friend,user,answer):
        with self.store.connect() as db:
            for role,text in [('user',user),('assistant',answer)]: db.execute('INSERT INTO dialogs(id,owner,friend,role,content,created) VALUES (?,?,?,?,?,?)',(str(uuid.uuid4()),owner,friend,role,text,time.time()))

    def open_conversation(self,owner,friend,reading_id=None):
        if friend not in FRIENDS: raise ValueError('未知朋友')
        if reading_id: self.store.get(reading_id,owner)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            key=reading_id or 'daily'
            db.execute("INSERT OR IGNORE INTO conversations VALUES (?,?,?,?,?,'active',0,?)",(str(uuid.uuid4()),owner,friend,reading_id,key,time.time()))
            c=dict(db.execute('SELECT * FROM conversations WHERE owner=? AND friend=? AND reading_key=?',(owner,friend,key)).fetchone())
            if c['state']!='active': raise KeyError('此会话已停用')
            return c

    def conversation(self,owner,friend,cid):
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM conversations WHERE owner=? AND friend=? AND id=?',(owner,friend,cid)).fetchone()
        if not row: raise KeyError()
        if row['state']!='active':
            from .service import Gone
            raise Gone('关联结果已删除或过期，此会话已清除')
        return dict(row)

    def clear_conversations(self,owner,friend):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE operations SET state='gone',response=NULL WHERE owner=? AND scope IN (SELECT 'chat:'||id FROM conversations WHERE owner=? AND friend=?)",(owner,owner,friend))
            db.execute('DELETE FROM dialogs WHERE owner=? AND friend=?',(owner,friend))
            # Keep ID so a concurrent stale response cannot recreate deleted messages.
            db.execute('UPDATE conversations SET context_after=? WHERE owner=? AND friend=?',(time.time(),owner,friend))
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
