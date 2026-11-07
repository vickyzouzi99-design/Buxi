"""Run after pip install -r server/requirements-dev.txt."""
import os
import tempfile
import unittest
from unittest.mock import patch
try:
    from fastapi.testclient import TestClient
    from server.app.main import app
    AVAILABLE=True
except ImportError:
    AVAILABLE=False

@unittest.skipUnless(AVAILABLE,"FastAPI/httpx not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"BUXI_DATA_DIR":self.temp.name,"MODEL_API_KEY":"","MODEL_NAME":""})
        self.env.start()
        self.client=TestClient(app)
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.env.stop(); self.temp.cleanup()
    def test_roundtrip_and_failed_ai(self):
        payload={"question":"test","spread":"three","request_key":"api-test-001"}
        r=self.client.post("/api/results/tarot",json=payload)
        self.assertEqual(r.status_code,200)
        rid=r.json()["id"]
        self.assertEqual(self.client.post("/api/results/tarot",json=payload).json()["id"],rid)
        self.assertEqual(self.client.post(f"/api/results/{rid}/interpretations").status_code,503)
        self.assertEqual(self.client.get(f"/api/results/{rid}").json()["cards"],r.json()["cards"])
        self.assertEqual(self.client.delete(f"/api/results/{rid}").status_code,200)
        self.assertEqual(self.client.get(f"/api/results/{rid}").status_code,404)
    def test_origin_and_validation(self):
        self.assertEqual(self.client.post("/api/results/tarot",json={},headers={"Origin":"https://evil.example"}).status_code,403)
        self.assertEqual(self.client.post("/api/results/tarot",json={}).status_code,422)

if __name__=="__main__": unittest.main()
