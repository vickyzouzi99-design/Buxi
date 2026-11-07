"""Dependency-free LOCAL preview adapter; production API is FastAPI.
Uses the same application services, so draws and persistence are real.
Never bind this development server to a public interface.
"""
import json
import mimetypes
import os
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.app.config import load_env
load_env()
from server.app.service import Store, Conflict
from server.app import model

ROOT=Path(__file__).resolve().parents[1]
store=Store()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send_json(self,data,status=200):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch()
    def do_DELETE(self): self.dispatch()
    def dispatch(self):
        try:
            if self.headers.get("Host","").split(":")[0] not in ("localhost","127.0.0.1"):
                return self.send_json({"detail":"Invalid host"},403)
            if self.command!="GET":
                if self.headers.get("Origin") not in (None,"http://localhost:8080","http://127.0.0.1:8080"):
                    return self.send_json({"detail":"不允许的请求来源"},403)
            path=urlparse(self.path).path
            data={}
            if self.command=="POST":
                size=int(self.headers.get("Content-Length","0"))
                if size>16000: return self.send_json({"detail":"请求过大"},413)
                data=json.loads(self.rfile.read(size) or b"{}")
                if not isinstance(data,dict): raise ValueError("需要 JSON 对象")
            if path in ("/health/live","/health/ready","/api/status"):
                return self.send_json({"status":"ready","version":"0.1.0","model_configured":model.configured(),"mode":"local-preview","available":["tarot"]})
            if path=="/api/results" and self.command=="GET":
                return self.send_json(store.list())
            if path=="/api/export" and self.command=="GET":
                records=store.list()
                return self.send_json({"version":1,"records":records,"messages":{r["id"]:store.messages(r["id"]) for r in records}})
            if path=="/api/results/tarot" and self.command=="POST":
                return self.send_json(store.create(data.get("question",""),data.get("spread","single"),data.get("request_key","")))
            if path.startswith("/api/results/"):
                bits=path.strip("/").split("/")
                result=store.get(bits[2])
                if len(bits)==3 and self.command=="GET": return self.send_json(result)
                if len(bits)==3 and self.command=="DELETE":
                    store.delete(result["id"]); return self.send_json({"deleted":True})
                if len(bits)==4 and bits[3]=="interpretations" and self.command=="POST":
                    return self.send_json(store.set_interpretation(result["id"],model.interpret(result),os.environ.get("MODEL_NAME")))
                if len(bits)==4 and bits[3]=="messages":
                    if self.command=="GET": return self.send_json(store.messages(result["id"]))
                    if self.command=="POST":
                        message=data.get("message","").strip()
                        if not message or len(message)>2000: raise ValueError("请输入 1–2000 字的消息")
                        reply=model.chat(result,store.messages(result["id"]),message)
                        store.add_exchange(result["id"],message,reply)
                        return self.send_json({"role":"assistant","content":reply})
                return self.send_json({"detail":"接口不存在"},404)
            if path.startswith("/api/"): return self.send_json({"detail":"接口不存在"},404)
            if self.command!="GET": return self.send_json({"detail":"方法不支持"},405)
            root=(ROOT/"web"/"dist").resolve()
            target=(root/path.lstrip("/")).resolve()
            if not target.is_relative_to(root): return self.send_json({"detail":"Forbidden"},403)
            if not target.is_file(): target=root/"index.html"
            if not target.exists(): return self.send_json({"detail":"请先在 web 目录运行 npm run build"},503)
            body=target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type",mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers(); self.wfile.write(body)
        except Conflict as exc: self.send_json({"detail":str(exc)},409)
        except KeyError: self.send_json({"detail":"记录不存在"},404)
        except model.ModelError as exc: self.send_json({"detail":str(exc)},503)
        except (ValueError,TypeError,AttributeError): self.send_json({"detail":"输入格式无效"},422)

if __name__=="__main__":
    print("Buxi local preview: http://127.0.0.1:8080",flush=True)
    ThreadingHTTPServer(("127.0.0.1",8080),Handler).serve_forever()
