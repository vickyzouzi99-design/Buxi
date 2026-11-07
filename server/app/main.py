"""FastAPI entry point. Local-only M0/M1; no multi-user authentication yet."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .config import load_env
load_env()
from .service import Store, Conflict
from . import model

@asynccontextmanager
async def lifespan(app):
    app.state.store=Store()
    yield

app=FastAPI(title="卜犀 Buxi",version="0.1.0",lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=["localhost","127.0.0.1","testserver","api"])

@app.middleware("http")
async def local_origin(request: Request,call_next):
    # CORS alone does not prevent requests. Reject cross-site mutations explicitly.
    if request.method not in ("GET","HEAD","OPTIONS"):
        origin=request.headers.get("origin")
        allowed={"http://localhost:8080","http://127.0.0.1:8080","http://localhost:5173","http://127.0.0.1:5173"}
        if origin and origin not in allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail":"不允许的请求来源"},status_code=403)
    return await call_next(request)

class DrawInput(BaseModel):
    question: str=Field(default="",max_length=1000)
    spread: str="single"
    request_key: str=Field(min_length=8,max_length=100)

class ChatInput(BaseModel):
    message: str=Field(min_length=1,max_length=2000)

@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/health/ready")
def ready():
    app.state.store.list()
    return {"status":"ready","model_configured":model.configured()}
@app.get("/api/status")
def status():
    return {"version":"0.1.0","model_configured":model.configured(),"mode":"local","available":["tarot"]}

@app.get("/api/results")
def results(): return app.state.store.list()

@app.post("/api/results/tarot")
def create(data:DrawInput):
    try: return app.state.store.create(data.question,data.spread,data.request_key)
    except Conflict as exc: raise HTTPException(409,str(exc))
    except ValueError as exc: raise HTTPException(422,str(exc))

def get_result(result_id):
    try: return app.state.store.get(result_id)
    except KeyError: raise HTTPException(404,"记录不存在")

@app.get("/api/results/{result_id}")
def get(result_id:str): return get_result(result_id)

@app.delete("/api/results/{result_id}")
def delete(result_id:str):
    get_result(result_id)
    app.state.store.delete(result_id)
    return {"deleted":True}

@app.post("/api/results/{result_id}/interpretations")
def interpret(result_id:str):
    result=get_result(result_id)
    try:
        text=model.interpret(result)
        return app.state.store.set_interpretation(result_id,text,os.environ.get("MODEL_NAME"))
    except model.ModelError as exc: raise HTTPException(503,str(exc))

@app.get("/api/results/{result_id}/messages")
def messages(result_id:str):
    get_result(result_id)
    return app.state.store.messages(result_id)

@app.post("/api/results/{result_id}/messages")
def chat(result_id:str,data:ChatInput):
    result=get_result(result_id)
    if not data.message.strip(): raise HTTPException(422,"请输入消息")
    try:
        text=model.chat(result,app.state.store.messages(result_id),data.message.strip())
        app.state.store.add_exchange(result_id,data.message.strip(),text)
        return {"role":"assistant","content":text}
    except model.ModelError as exc: raise HTTPException(503,str(exc))

@app.get("/api/export")
def export():
    records=app.state.store.list()
    return {"version":1,"records":records,"messages":{r["id"]:app.state.store.messages(r["id"]) for r in records}}
