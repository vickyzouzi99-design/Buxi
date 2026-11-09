"""Local single-owner service. SQLite transaction makes draw retries idempotent."""
from contextlib import contextmanager
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .tarot import draw, reflection

class Conflict(ValueError):
    pass

class Store:
    def __init__(self, path=None):
        self.path = Path(path or Path(os.getenv("BUXI_DATA_DIR","data")) / "buxi.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, request_key TEXT NOT NULL,
                payload TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(owner_id, request_key));
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, result_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            db.execute("PRAGMA user_version=1")
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
    def create(self, question, spread, request_key, owner="local", allow_reversed=True, system="tarot", save=True):
        question=question.strip()
        if len(question)>1000 or not 8 <= len(request_key) <= 100:
            raise ValueError("问题过长或请求标识无效")
        payload=json.dumps({"question":question,"spread":spread,"allow_reversed":allow_reversed,"system":system},ensure_ascii=False,sort_keys=True)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old=db.execute("SELECT payload,content FROM results WHERE owner_id=? AND request_key=?",
                           (owner,request_key)).fetchone()
            if old:
                if old["payload"] != payload:
                    raise Conflict("同一请求标识不能用于不同的问题")
                return json.loads(old["content"])
            if system=='tarot': cards=draw(spread,allow_reversed=allow_reversed)
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
            db.execute("INSERT INTO results VALUES (?,?,?,?,?,?)",
                       (result["id"],owner,request_key,payload,json.dumps(result,ensure_ascii=False),result["created_at"]))
            return result
    def get(self, result_id, owner="local"):
        with self.connect() as db:
            row=db.execute("SELECT content FROM results WHERE id=? AND owner_id=?",(result_id,owner)).fetchone()
        if not row:
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
    def delete(self,result_id,owner="local"):
        self.get(result_id,owner)
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE result_id=?",(result_id,))
            db.execute("DELETE FROM results WHERE id=? AND owner_id=?",(result_id,owner))
