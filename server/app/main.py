"""Private beta API. Every personal route derives its owner from an HttpOnly session."""
import os,time,threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI,HTTPException,Request,Depends,Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .config import load_env
load_env()
from .service import Store,Conflict,Gone
from .accounts import Accounts
from .rules import FRIENDS
from . import model,knowledge
import json,uuid

@asynccontextmanager
async def lifespan(app):
    app.state.store=Store();app.state.accounts=Accounts(app.state.store)
    # Public professional retrieval is file-backed and read-only; no startup embedding calls.
    yield
app=FastAPI(title='卜犀 Buxi',version='0.3.0',lifespan=lifespan)
lock=threading.Lock(); attempts={}
@app.middleware('http')
async def boundary(request,call_next):
    hosts=os.getenv('BUXI_ALLOWED_HOSTS','localhost,127.0.0.1,testserver,api').split(',')
    if request.url.hostname not in hosts: return JSONResponse({'detail':'不允许的主机'},403)
    allowed=os.getenv('BUXI_ALLOWED_ORIGINS','http://localhost:8080,http://127.0.0.1:8080,http://testserver').split(',')
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('origin') not in [None,*allowed]: return JSONResponse({'detail':'不允许的来源'},403)
    response=await call_next(request)
    if request.url.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
    return response
@app.exception_handler(PermissionError)
async def denied(request,exc): return JSONResponse({'detail':str(exc)},401)
@app.exception_handler(KeyError)
async def missing(request,exc): return JSONResponse({'detail':'记录不存在'},404)
@app.exception_handler(Gone)
async def gone(request,exc): return JSONResponse({'detail':'结果已删除或过期；关联聊天已清除，请开始新的体验。'},410)
@app.exception_handler(Conflict)
async def conflict(request,exc): return JSONResponse({'detail':str(exc)},409)
@app.exception_handler(ValueError)
async def invalid(request,exc): return JSONResponse({'detail':str(exc)},422)
@app.exception_handler(model.ModelError)
async def unavailable(request,exc): return JSONResponse({'detail':str(exc)},503)
def owner(request:Request): return app.state.accounts.owner(request.cookies.get('buxi_session',''))
class Login(BaseModel): code:str=Field(min_length=1,max_length=100)
@app.post('/api/login')
def login(data:Login,request:Request,response:Response):
    ip=request.client.host if request.client else 'unknown';now=time.time()
    with lock:
        for key in list(attempts):
            if now-attempts[key][0]>60: del attempts[key]
        start,count=attempts.get(ip,(now,0))
        if count>=10: raise HTTPException(429,'请一分钟后再试')
        attempts[ip]=(start,count+1)
    token=app.state.accounts.login(data.code.strip())
    response.set_cookie('buxi_session',token,httponly=True,samesite='strict',secure=os.getenv('BUXI_SECURE_COOKIE')=='1',max_age=604800)
    return {'ok':True}
@app.post('/api/logout')
def logout(request:Request,response:Response):
    app.state.accounts.logout(request.cookies.get('buxi_session',''));response.delete_cookie('buxi_session');return {'ok':True}
@app.get('/health/live')
def live(): return {'status':'ok'}
@app.get('/health/ready')
def ready(): return {'status':'ready'}
@app.get('/api/status')
def status(who=Depends(owner)):
    return {'version':'0.3.0','owner_id':who,'knowledge_version':knowledge.VERSION,'model_configured':model.configured(),'friends':FRIENDS,'prefs':app.state.accounts.prefs(who),'embedding_mode':'semantic' if os.getenv('EMBEDDING_MODEL') else 'local_lexical','available':['tarot','sticks']}
class DrawInput(BaseModel):
    question:str=Field(default='',max_length=1000)
    spread:Literal['single','three','reflection']='three'
    request_key:str=Field(min_length=8,max_length=100)
    allow_reversed:bool=True
    save:bool=False
    select_cards:bool=False
@app.post('/api/results/{system}')
def draw(system:str,data:DrawInput,who=Depends(owner)):
    cleanup(who)
    return app.state.store.create(data.question,data.spread,data.request_key,who,data.allow_reversed,system,data.save,data.select_cards)
# Unconfirmed draws expire after 24h; they are available only to their owner in the interim.
def cleanup(who):
    from datetime import datetime,timezone
    for r in app.state.store.list(who):
        if not r.get('saved',True) and time.time()-datetime.fromisoformat(r['created_at']).timestamp()>86400: app.state.store.delete(r['id'],who,'expired')
def result(rid,who):
    cleanup(who);return app.state.store.get(rid,who)
@app.get('/api/results')
def results(who=Depends(owner)):
    cleanup(who);return [r for r in app.state.store.list(who) if r.get('saved',True)]
@app.get('/api/results/{rid}')
def get(rid:str,who=Depends(owner)):
    r=result(rid,who);r['generation_status']=app.state.store.operation_state(who,'interpret:'+rid);return r
@app.post('/api/results/{rid}/save')
def save(rid:str,who=Depends(owner)):
    result(rid,who)
    with app.state.store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT content FROM results WHERE id=? AND owner_id=?',(rid,who)).fetchone()
        if not row: raise Gone()
        r=json.loads(row[0]);r['saved']=True
        db.execute('UPDATE results SET content=? WHERE id=? AND owner_id=?',(json.dumps(r,ensure_ascii=False),rid,who))
    return r
@app.delete('/api/results/{rid}')
def delete(rid:str,who=Depends(owner)):
    app.state.store.delete(rid,who);return {'ok':True}
class RetryInput(BaseModel):
    request_key:str=Field(default='initial-reading-v1',min_length=8,max_length=100)

class RevealInput(BaseModel):
    revealed:list[str]=Field(max_length=78)

class PickInput(BaseModel):
    slot:int=Field(ge=0,lt=78,strict=True)
    order:int=Field(ge=0,lt=3,strict=True)

@app.post('/api/results/{rid}/picks')
def pick(rid:str,data:PickInput,who=Depends(owner)):
    result(rid,who)
    return app.state.store.pick(rid,data.slot,data.order,who)

def require_selected(r):
    if r.get('selection',{}).get('status')=='picking': raise Conflict('先选好这次的牌，再继续吧')

@app.put('/api/results/{rid}/reveal')
def reveal(rid:str,data:RevealInput,who=Depends(owner)):
    result(rid,who);return app.state.store.reveal(rid,data.revealed,who)

@app.post('/api/results/{rid}/interpretations')
def interpret(rid:str,data:RetryInput=RetryInput(),who=Depends(owner)):
    r=result(rid,who);store=app.state.store;scope='interpret:'+rid
    require_selected(r)
    token,cached=store.claim(who,scope,data.request_key,{'rid':rid})
    if cached is not None: return get(rid,who)
    try:
        text=model.interpret(r);refs=knowledge.references(r);citations=model.validate(text,refs,True)
        result(rid,who)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT content FROM results WHERE id=? AND owner_id=?',(rid,who)).fetchone()
            if not row: raise Gone()
            current=json.loads(row[0]);current.update(interpretation=text,interpretation_source='ai',citations=citations,generation_status='done',**model.generation_metadata())
            store.finish(db,who,scope,data.request_key,token,{'id':rid})
            db.execute('UPDATE results SET content=? WHERE id=?',(json.dumps(current,ensure_ascii=False),rid))
            return current
    except Exception:
        store.fail(who,scope,data.request_key,token);raise
class ChatInput(BaseModel):
    message:str=Field(min_length=1,max_length=2000)
    reading_id:str|None=None
    conversation_id:str|None=None
    request_key:str=Field(default_factory=lambda:str(uuid.uuid4()),min_length=8,max_length=100)

class ConversationInput(BaseModel):
    reading_id:str|None=None

@app.post('/api/friends/{friend}/conversations')
def open_conversation(friend:str,data:ConversationInput,who=Depends(owner)):
    if data.reading_id: require_selected(result(data.reading_id,who))
    c=app.state.accounts.open_conversation(who,friend,data.reading_id)
    return conversation(friend,c['id'],who)

@app.get('/api/friends/{friend}/conversations')
def conversations(friend:str,who=Depends(owner)):
    cleanup(who)
    with app.state.store.connect() as db:
        return [dict(r) for r in db.execute("SELECT id,reading_id,state,created FROM conversations WHERE owner=? AND friend=? ORDER BY created DESC",(who,friend))]

@app.get('/api/friends/{friend}/conversations/{cid}')
def conversation(friend:str,cid:str,who=Depends(owner)):
    cleanup(who);c=app.state.accounts.conversation(who,friend,cid)
    return dict(c,messages=app.state.accounts.history(who,friend,cid),reading=result(c['reading_id'],who) if c['reading_id'] else None,generation_status=app.state.store.operation_state(who,'chat:'+cid))
@app.get('/api/friends/{friend}/messages')
def history(friend:str,who=Depends(owner)):
    if friend not in FRIENDS: raise ValueError('未知朋友')
    cleanup(who)
    return app.state.accounts.history(who,friend)
@app.delete('/api/friends/{friend}/messages')
def clear_chat(friend:str,who=Depends(owner)):
    app.state.accounts.clear_conversations(who,friend)
    return {'ok':True}
@app.post('/api/friends/{friend}/messages')
def chat(friend:str,data:ChatInput,who=Depends(owner)):
    if friend not in FRIENDS or not data.message.strip(): raise ValueError('消息无效')
    cleanup(who);accounts=app.state.accounts;store=app.state.store
    c=accounts.conversation(who,friend,data.conversation_id) if data.conversation_id else accounts.open_conversation(who,friend,data.reading_id)
    if data.reading_id and c['reading_id']!=data.reading_id: raise Conflict('不能将另一牌阵加入当前会话，请明确打开新的会话')
    r=result(c['reading_id'],who) if c['reading_id'] else None
    if r: require_selected(r)
    scope='chat:'+c['id'];token,cached=store.claim(who,scope,data.request_key,{'message':data.message,'reading_id':c['reading_id']})
    if cached is not None: return cached
    try:
        memories=accounts.recall(who,friend,data.message)
        history=accounts.history(who,friend,c['id'],context=True)
        refs=knowledge.references(r,data.message) if friend=='feiyue' or r else []
        reply=model.chat(r,history,data.message,friend,memories)
        citations=model.validate(reply,refs,required=bool(knowledge.search(data.message)) and friend=='feiyue')
        if r: result(r['id'],who)
        response={'role':'assistant','content':reply,'conversation_id':c['id'],'reading_id':c['reading_id'],'memory_sources':[m['id'] for m in memories],'citations':citations,'provided_entries':[x['entry_id'] for x in refs],**model.generation_metadata()}
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT state,context_after FROM conversations WHERE id=? AND owner=?',(c['id'],who)).fetchone()
            if not current or current['state']!='active': raise Gone()
            if current['context_after']!=c['context_after']: raise Conflict('记忆或聊天已变更，本次回复已取消，请用原消息重试')
            store.finish(db,who,scope,data.request_key,token,response)
            for role,content,meta in [('user',data.message,{}),('assistant',reply,{k:v for k,v in response.items() if k not in ('role','content','conversation_id')})]:
                db.execute('INSERT INTO dialogs VALUES (?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),who,friend,role,content,time.time(),c['id'],json.dumps(meta,ensure_ascii=False)))
        return response
    except Exception:
        store.fail(who,scope,data.request_key,token);raise
class MemoryInput(BaseModel):
    friend:Literal['feiyue','xingche','zhiwei']
    content:str=Field(min_length=1,max_length=1000)
    active:bool=True
@app.get('/api/memories')
def memories(who=Depends(owner)): return app.state.accounts.memories(who)
@app.post('/api/memories')
def remember(data:MemoryInput,who=Depends(owner)):
    return {'id':app.state.accounts.save_memory(who,data.friend,data.content,'用户确认保存',active=data.active)}
@app.put('/api/memories/{mid}')
def update_memory(mid:str,data:MemoryInput,who=Depends(owner)):
    return {'id':app.state.accounts.save_memory(who,data.friend,data.content,'用户确认修改',mid,data.active)}
@app.delete('/api/memories/{mid}')
def forget(mid:str,who=Depends(owner)):
    app.state.accounts.delete_memory(who,mid);return {'ok':True}
class Prefs(BaseModel): greetings:bool
@app.put('/api/preferences')
def prefs(data:Prefs,who=Depends(owner)): return app.state.accounts.prefs(who,data.greetings)
@app.post('/api/greeting')
def greeting(who=Depends(owner)): return app.state.accounts.greet(who)
@app.get('/api/export')
def export(who=Depends(owner)):
    return {'version':2,'records':results(who),'memories':memories(who),'dialogs':{f:app.state.accounts.history(who,f) for f in FRIENDS},'legacy_messages':{r['id']:app.state.store.messages(r['id'],who) for r in results(who)}}
@app.get('/api/knowledge')
def search_knowledge(q:str='',who=Depends(owner)):
    if not 1<=len(q.strip())<=200: raise ValueError('请输入1–200字的检索内容')
    return knowledge.public_hits(q)
@app.get('/api/knowledge/cards/{card_id}')
def exact_knowledge(card_id:str,orientation:Literal['upright','reversed']='upright',knowledge_version:str=knowledge.VERSION,who=Depends(owner)):
    return knowledge.exact(card_id,orientation,knowledge_version)
@app.get('/api/results/{rid}/messages')
def legacy_messages(rid:str,who=Depends(owner)):
    result(rid,who);return app.state.store.messages(rid,who)
# Built UI and API share one origin; never expose source, .env, or data directories.
dist=Path(__file__).resolve().parents[2]/'web/dist'
if dist.exists(): app.mount('/',StaticFiles(directory=dist,html=True),name='web')
