"""Local single-owner service. SQLite transaction makes draw retries idempotent."""
from contextlib import contextmanager, closing
import json
import os
import sqlite3
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from .tarot import draw, reflection

class Conflict(ValueError):
    pass

class Gone(KeyError):
    pass

class Store:
    def __init__(self, path=None):
        self.path = Path(path or Path(os.getenv("BUXI_DATA_DIR","data")) / "buxi.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # SQLite online backup includes committed WAL contents. Never overwrite a backup.
        if self.path.exists():
            with closing(sqlite3.connect(self.path)) as old:
                version=old.execute('PRAGMA user_version').fetchone()[0]
                if version < 4:
                    backup=self.path.with_name(self.path.name+'.pre-v4-'+uuid.uuid4().hex[:8]+'.bak')
                    with closing(sqlite3.connect(backup)) as dest: old.backup(dest)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, request_key TEXT NOT NULL,
                payload TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(owner_id, request_key));
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, result_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tombstones(owner TEXT NOT NULL, request_key TEXT NOT NULL, result_id TEXT NOT NULL, reason TEXT NOT NULL, PRIMARY KEY(owner,request_key));
            CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, owner TEXT NOT NULL, friend TEXT NOT NULL, reading_id TEXT, reading_key TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'active', context_after REAL NOT NULL DEFAULT 0, created REAL NOT NULL, UNIQUE(owner,friend,reading_key));
            CREATE TABLE IF NOT EXISTS operations(owner TEXT NOT NULL, scope TEXT NOT NULL, request_key TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, token TEXT NOT NULL, started REAL NOT NULL, response TEXT, PRIMARY KEY(owner,scope,request_key));
            CREATE TABLE IF NOT EXISTS hidden_decks(result_id TEXT PRIMARY KEY, content TEXT NOT NULL);
            """)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path, timeout=10)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()
    def create(self, question, spread, request_key, owner="local", allow_reversed=True, system="tarot", save=True, select_cards=False):
        question=question.strip()
        if len(question)>1000 or not 8 <= len(request_key) <= 100:
            raise ValueError("问题过长或请求标识无效")
        payload=json.dumps({"question":question,"spread":spread,"allow_reversed":allow_reversed,"system":system},ensure_ascii=False,sort_keys=True)
        if select_cards:
            if system!='tarot': raise ValueError('只有塔罗支持选牌')
            payload=json.dumps(dict(json.loads(payload),select_cards=True),ensure_ascii=False,sort_keys=True)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute('SELECT 1 FROM tombstones WHERE owner=? AND request_key=?',(owner,request_key)).fetchone():
                raise Gone('结果已删除或过期，请明确开始新的体验')
            old=db.execute("SELECT payload,content FROM results WHERE owner_id=? AND request_key=?",
                           (owner,request_key)).fetchone()
            if old:
                if old["payload"] != payload:
                    raise Conflict("同一请求标识不能用于不同的问题")
                return json.loads(old["content"])
            if system=='tarot':
                from .spreads import SPREADS
                if spread not in SPREADS: raise ValueError('不支持的牌阵')
                cards=[] if select_cards else draw(spread,allow_reversed=allow_reversed)
            elif system=='sticks':
                from .rules import STICKS
                import secrets
                index=secrets.randbelow(len(STICKS)); title,prompt=STICKS[index]
                cards=[dict(id=f'stick-{index+1}',name=title,kind='卜犀原创签',position=f'第 {index+1} 签',reversed=False,prompt=prompt)]
            else: raise ValueError('不支持的工具')
            result={"id":str(uuid.uuid4()),"system":system,"saved":save,"question":question,"spread":spread,
                    "cards":cards,"created_at":datetime.now(timezone.utc).isoformat(),
                    "algorithm_version":"draw-remove-v2","allow_reversed":allow_reversed,"interpretation":reflection(cards) if system=="tarot" else cards[0]["prompt"],
                    "interpretation_source":"local_reflection","model":None}
            result.update(revealed=[], generation_status='idle')
            if select_cards:
                from .tarot import shuffled_deck
                result.update(selection={'status':'picking','total':78,'picked':[],'positions':SPREADS[spread]},
                              algorithm_version='shuffle-pick-v1',interpretation='',interpretation_source='pending_selection')
                hidden=shuffled_deck(allow_reversed)
                db.execute('INSERT INTO hidden_decks VALUES (?,?)',(result['id'],json.dumps(hidden,ensure_ascii=False)))
            elif system=='tarot':
                self.decorate_tarot(result)
            db.execute("INSERT INTO results VALUES (?,?,?,?,?,?)",
                       (result["id"],owner,request_key,payload,json.dumps(result,ensure_ascii=False),result["created_at"]))
            return result
    def decorate_tarot(self, result):
        cards=result["cards"];spread=result["spread"]
        from . import knowledge
        from .rules import SPREAD_VERSION, SPREAD_DEFINITIONS
        refs=knowledge.snapshot(cards)
        for c,p,r in zip(cards,SPREAD_DEFINITIONS[spread],refs):
            c['position_id']=p['id'];c['position_definition']=p['meaning'];c['prompt']=r['text']
            # Preserve Tarotoo in its own source branch, not in the default prompt.
            c.pop('meanings',None);c.pop('contexts',None);c.pop('keywords',None);c.pop('source',None)
        result.update(knowledge_version=knowledge.VERSION, knowledge_snapshot=refs,
                      spread_version=SPREAD_VERSION, interpretation_policy=knowledge.POLICY_VERSION,
                      persona_version=knowledge.PERSONA_VERSION,prompt_version=knowledge.PROMPT_VERSION,
                      interpretation='这组牌可以作为观察当下的几个角度。以下是项目编辑初稿，结合你的具体处境仍需进一步讨论。\n\n'+'\n\n'.join(f"{c['position']} · {c['name']}（{'逆位' if c['reversed'] else '正位'}）\n{r['text']}" for c,r in zip(cards,refs)),interpretation_source='editorial_draft', citations=knowledge.label(refs))

    def get(self, result_id, owner="local"):
        with self.connect() as db:
            row=db.execute("SELECT content FROM results WHERE id=? AND owner_id=?",(result_id,owner)).fetchone()
        if not row:
            with self.connect() as db:
                if db.execute('SELECT 1 FROM tombstones WHERE owner=? AND result_id=?',(owner,result_id)).fetchone():
                    raise Gone('结果已删除或过期，关联聊天已停用')
            raise KeyError("记录不存在")
        return json.loads(row["content"])
    def list(self, owner="local"):
        with self.connect() as db:
            rows=db.execute("SELECT content FROM results WHERE owner_id=? ORDER BY created_at DESC",(owner,)).fetchall()
        return [json.loads(row["content"]) for row in rows]
    def set_interpretation(self,result_id,text,model,owner="local"):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT content FROM results WHERE id=? AND owner_id=?",(result_id,owner)).fetchone()
            if not row: raise KeyError("记录不存在")
            result=json.loads(row["content"])
            result.update(interpretation=text,interpretation_source="ai",model=model)
            db.execute("UPDATE results SET content=? WHERE id=?",(json.dumps(result,ensure_ascii=False),result_id))
        return result
    def messages(self,result_id,owner="local"):
        self.get(result_id,owner)
        with self.connect() as db:
            rows=db.execute("SELECT role,content FROM messages WHERE result_id=? ORDER BY rowid",(result_id,)).fetchall()
        return [dict(row) for row in rows]
    def add_exchange(self,result_id,user,assistant,owner="local"):
        self.get(result_id,owner)
        with self.connect() as db:
            for role,content in [("user",user),("assistant",assistant)]:
                db.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
                           (str(uuid.uuid4()),result_id,role,content,datetime.now(timezone.utc).isoformat()))
    def delete(self,result_id,owner="local",reason='deleted'):
        self.get(result_id,owner)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO tombstones SELECT owner_id,request_key,id,? FROM results WHERE id=? AND owner_id=?',(reason,result_id,owner))
            db.execute("DELETE FROM messages WHERE result_id=?",(result_id,))
            ids=[r[0] for r in db.execute('SELECT id FROM conversations WHERE owner=? AND reading_id=?',(owner,result_id))]
            for cid in ids:
                db.execute('DELETE FROM dialogs WHERE owner=? AND conversation_id=?',(owner,cid))
                db.execute("UPDATE operations SET state='gone',response=NULL,payload='{}' WHERE owner=? AND scope=?",(owner,'chat:'+cid))
            db.execute("UPDATE conversations SET state=? WHERE owner=? AND reading_id=?",(reason,owner,result_id))
            db.execute("UPDATE operations SET state='gone',response=NULL,payload='{}' WHERE owner=? AND scope=?",(owner,'interpret:'+result_id))
            db.execute("DELETE FROM results WHERE id=? AND owner_id=?",(result_id,owner))
            db.execute('DELETE FROM hidden_decks WHERE result_id=?',(result_id,))

    def pick(self, rid, slot, order, owner):
        self.get(rid,owner)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT content FROM results WHERE id=? AND owner_id=?',(rid,owner)).fetchone()
            if not row: raise Gone()
            r=json.loads(row[0]);selection=r.get('selection')
            if not selection: raise Conflict('这次体验不需要选牌')
            picked=selection['picked']
            if order<len(picked):
                if picked[order]==slot: return r
                raise Conflict('这个牌位已经选好，请刷新查看')
            if order!=len(picked) or selection['status']!='picking': raise Conflict('选牌进度已更新，请刷新查看')
            if not 0<=slot<selection['total'] or slot in picked: raise ValueError('请选择尚未选过的牌')
            picked.append(slot)
            if len(picked)==len(selection['positions']):
                hidden=json.loads(db.execute('SELECT content FROM hidden_decks WHERE result_id=?',(rid,)).fetchone()[0])
                r['cards']=[dict(hidden[i],position=position) for i,position in zip(picked,selection['positions'])]
                self.decorate_tarot(r)
                selection['status']='complete'
                db.execute('DELETE FROM hidden_decks WHERE result_id=?',(rid,))
            db.execute('UPDATE results SET content=? WHERE id=?',(json.dumps(r,ensure_ascii=False),rid))
            return r

    def reveal(self, rid, ids, owner):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT content FROM results WHERE id=? AND owner_id=?',(rid,owner)).fetchone()
            if not row: raise KeyError()
            r=json.loads(row[0]); valid={c['id'] for c in r['cards']}
            if set(ids)-valid: raise ValueError('翻牌进度包含其他牌')
            r['revealed']=sorted(set(r.get('revealed',[]))|set(ids))
            db.execute('UPDATE results SET content=? WHERE id=?',(json.dumps(r,ensure_ascii=False),rid))
            return r

    def claim(self, owner, scope, key, payload):
        encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM operations WHERE owner=? AND scope=? AND request_key=?',(owner,scope,key)).fetchone()
            if row:
                if row['state']=='gone': raise Gone('内容已删除或过期')
                if row['payload']!=encoded: raise Conflict('同一请求标识不能用于不同内容')
                if row['state']=='done': return None,json.loads(row['response'])
            active=db.execute("SELECT 1 FROM operations WHERE owner=? AND scope=? AND state='running' AND started>?",(owner,scope,time.time()-90)).fetchone()
            if active: raise Conflict('正在处理同一会话，请稍后用原请求重试')
            db.execute("UPDATE operations SET state='failed' WHERE owner=? AND scope=? AND state='running' AND started<=?",(owner,scope,time.time()-90))
            token=uuid.uuid4().hex
            db.execute('INSERT OR REPLACE INTO operations VALUES (?,?,?,?,?,?,?,?)',(owner,scope,key,encoded,'running',token,time.time(),None))
            return token,None

    def operation_state(self, owner, scope):
        with self.connect() as db:
            row=db.execute('SELECT state,started FROM operations WHERE owner=? AND scope=? ORDER BY started DESC LIMIT 1',(owner,scope)).fetchone()
        if not row: return 'idle'
        return 'retryable' if row['state']=='running' and time.time()-row['started']>90 else row['state']

    def fail(self, owner, scope, key, token):
        with self.connect() as db: db.execute("UPDATE operations SET state='failed' WHERE owner=? AND scope=? AND request_key=? AND token=? AND state='running'",(owner,scope,key,token))

    def finish(self, db, owner, scope, key, token, response):
        count=db.execute("UPDATE operations SET state='done',response=? WHERE owner=? AND scope=? AND request_key=? AND token=? AND state='running'",(json.dumps(response,ensure_ascii=False),owner,scope,key,token)).rowcount
        if count!=1: raise Conflict('请求已被取消或被更新的重试取代')
