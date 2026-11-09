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
from .service import Store,Conflict
from .accounts import Accounts
from .rules import FRIENDS
from . import model

@asynccontextmanager
async def lifespan(app):
    app.state.store=Store();app.state.accounts=Accounts(app.state.store)
    with app.state.store.connect() as db:
        has_knowledge=db.execute('SELECT count(*) FROM knowledge').fetchone()[0]
    if not has_knowledge: app.state.accounts.index_knowledge()
    yield
app=FastAPI(title='卜犀 Buxi',version='0.2.0',lifespan=lifespan)
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
    return {'version':'0.2.0','model_configured':model.configured(),'friends':FRIENDS,'prefs':app.state.accounts.prefs(who),'embedding_mode':'semantic' if os.getenv('EMBEDDING_MODEL') else 'local_lexical','available':['tarot','sticks']}
class DrawInput(BaseModel):
    question:str=Field(default='',max_length=1000)
    spread:Literal['single','three','reflection']='three'
    request_key:str=Field(min_length=8,max_length=100)
    allow_reversed:bool=True
    save:bool=False
@app.post('/api/results/{system}')
def draw(system:str,data:DrawInput,who=Depends(owner)):
    return app.state.store.create(data.question,data.spread,data.request_key,who,data.allow_reversed,system,data.save)
# Unconfirmed draws expire after 24h; they are available only to their owner in the interim.
def cleanup(who):
    from datetime import datetime,timezone
    for r in app.state.store.list(who):
        if not r.get('saved',True) and time.time()-datetime.fromisoformat(r['created_at']).timestamp()>86400: app.state.store.delete(r['id'],who)
def result(rid,who):
    cleanup(who);return app.state.store.get(rid,who)
@app.get('/api/results')
def results(who=Depends(owner)):
    cleanup(who);return [r for r in app.state.store.list(who) if r.get('saved',True)]
@app.get('/api/results/{rid}')
def get(rid:str,who=Depends(owner)): return result(rid,who)
@app.post('/api/results/{rid}/save')
def save(rid:str,who=Depends(owner)):
    import json
    r=result(rid,who);r['saved']=True
    with app.state.store.connect() as db: db.execute('UPDATE results SET content=? WHERE id=? AND owner_id=?',(json.dumps(r,ensure_ascii=False),rid,who))
    return r
@app.delete('/api/results/{rid}')
def delete(rid:str,who=Depends(owner)):
    app.state.store.delete(rid,who);return {'ok':True}
@app.post('/api/results/{rid}/interpretations')
def interpret(rid:str,who=Depends(owner)):
    r=result(rid,who);return app.state.store.set_interpretation(rid,model.interpret(r),os.getenv('MODEL_NAME'),who)
class ChatInput(BaseModel):
    message:str=Field(min_length=1,max_length=2000)
    reading_id:str|None=None
@app.get('/api/friends/{friend}/messages')
def history(friend:str,who=Depends(owner)):
    if friend not in FRIENDS: raise ValueError('未知朋友')
    return app.state.accounts.history(who,friend)
@app.delete('/api/friends/{friend}/messages')
def clear_chat(friend:str,who=Depends(owner)):
    with app.state.store.connect() as db: db.execute('DELETE FROM dialogs WHERE owner=? AND friend=?',(who,friend))
    return {'ok':True}
@app.post('/api/friends/{friend}/messages')
def chat(friend:str,data:ChatInput,who=Depends(owner)):
    if friend not in FRIENDS or not data.message.strip(): raise ValueError('消息无效')
    r=result(data.reading_id,who) if data.reading_id else None
    memories=app.state.accounts.recall(who,friend,data.message)
    reply=model.chat(r,app.state.accounts.history(who,friend),data.message,friend,memories)
    app.state.accounts.exchange(who,friend,data.message,reply)
    return {'role':'assistant','content':reply,'memory_sources':[m['id'] for m in memories]}
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
def knowledge(q:str='',who=Depends(owner)):
    if not 1<=len(q.strip())<=200: raise ValueError('请输入1–200字的检索内容')
    return app.state.accounts.search_knowledge(q)
@app.get('/api/results/{rid}/messages')
def legacy_messages(rid:str,who=Depends(owner)):
    result(rid,who);return app.state.store.messages(rid,who)
# Built UI and API share one origin; never expose source, .env, or data directories.
dist=Path(__file__).resolve().parents[2]/'web/dist'
if dist.exists(): app.mount('/',StaticFiles(directory=dist,html=True),name='web')
