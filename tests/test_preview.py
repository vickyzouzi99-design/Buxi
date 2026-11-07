"""Exercise the real HTTP preview adapter with an isolated temp database."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch

class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.env=patch.dict(os.environ,{"BUXI_DATA_DIR":cls.temp.name,"MODEL_API_KEY":"","MODEL_NAME":""})
        cls.env.start()
        file=Path(__file__).resolve().parents[1]/"scripts"/"local_preview.py"
        spec=importlib.util.spec_from_file_location("buxi_preview",file)
        cls.preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.preview)
        cls.server=cls.preview.ThreadingHTTPServer(("127.0.0.1",0),cls.preview.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f"http://127.0.0.1:{cls.server.server_port}"
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        cls.env.stop();cls.temp.cleanup()
    def call(self,path,body=None,method=None,headers=None):
        raw=json.dumps(body).encode() if body is not None else None
        req=Request(self.url+path,data=raw,method=method,headers={"Content-Type":"application/json",**(headers or {})})
        try:
            with urlopen(req,timeout=5) as res: return res.status,res.read()
        except HTTPError as exc:return exc.code,exc.read()
    def test_ui_assets(self):
        for path in ["/","/main.js","/main.css"]:
            code,body=self.call(path)
            self.assertEqual(code,200);self.assertGreater(len(body),100)
        self.assertIn("卜犀".encode(),self.call("/")[1])
    def test_full_http_flow(self):
        data={"question":"本地运行测试","spread":"three","request_key":"http-roundtrip-001"}
        code,body=self.call("/api/results/tarot",data)
        self.assertEqual(code,200);r=json.loads(body);rid=r["id"]
        self.assertEqual(len(r["cards"]),3)
        self.assertEqual(json.loads(self.call("/api/results/tarot",data)[1])["id"],rid)
        code,_=self.call("/api/results/"+rid+"/interpretations",{})
        self.assertEqual(code,503)
        self.assertEqual(json.loads(self.call("/api/results/"+rid)[1])["cards"],r["cards"])
        export=json.loads(self.call("/api/export")[1])
        self.assertIn(rid,[x["id"] for x in export["records"]])
        self.assertEqual(self.call("/api/results/"+rid,method="DELETE")[0],200)
        self.assertEqual(self.call("/api/results/"+rid)[0],404)
    def test_reject_cross_site_and_bad_inputs(self):
        self.assertEqual(self.call("/api/results/tarot",{},headers={"Origin":"https://bad.example"})[0],403)
        self.assertEqual(self.call("/api/results/tarot",{"spread":"fake","request_key":"http-bad-001"})[0],422)
        self.assertEqual(self.call("/api/results/tarot",{"question":42,"request_key":"http-bad-002"})[0],422)

if __name__=="__main__":unittest.main()
