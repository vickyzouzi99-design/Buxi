"""The local launcher uses the same authenticated API; verify static routing."""
import unittest,tempfile,os
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app.main import app
class PreviewTests(unittest.TestCase):
 def test_static_assets_and_no_private_paths(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'BUXI_DATA_DIR':d,'EMBEDDING_MODEL':''}),TestClient(app) as client:
   for path in ['/','/main.js','/main.css']:
    r=client.get(path);self.assertEqual(r.status_code,200);self.assertGreater(len(r.content),100)
   for path in ['/.env','/data/buxi.db','/server/app/main.py']:
    self.assertEqual(client.get(path).status_code,404)
   self.assertEqual(client.get('/api/results').status_code,401)
