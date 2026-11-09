import os,tempfile,unittest,json
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app.main import app,attempts
from server.app import model

class ApiTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'BUXI_DATA_DIR':self.temp.name,'MODEL_API_KEY':'','MODEL_NAME':'','EMBEDDING_MODEL':''});self.env.start();attempts.clear()
  self.client=TestClient(app);self.client.__enter__();self.codes=app.state.accounts.issue(2)
  self.client.post('/api/login',json={'code':self.codes[0]})
 def tearDown(self):
  self.client.__exit__(None,None,None);self.env.stop();self.temp.cleanup()
 def draw(self,**kwargs):
  return self.client.post('/api/results/tarot',json={'question':'test','spread':'three','request_key':'api-test-001',**kwargs})
 def test_roundtrip_retry_and_failed_ai(self):
  r=self.draw().json();rid=r['id'];self.assertEqual(self.draw().json()['id'],rid)
  self.assertEqual(self.client.post(f'/api/results/{rid}/interpretations').status_code,503)
  self.assertEqual(self.client.get(f'/api/results/{rid}').json()['cards'],r['cards'])
  self.assertEqual(self.client.get('/api/results').json(),[])
  self.client.post(f'/api/results/{rid}/save');self.assertEqual(len(self.client.get('/api/results').json()),1)
  self.assertTrue(self.draw().json()['saved'])
 def test_scope_every_personal_endpoint(self):
  r=self.draw(save=True).json();rid=r['id']
  self.client.post('/api/login',json={'code':self.codes[1]})
  for method,path in [('get',f'/api/results/{rid}'),('delete',f'/api/results/{rid}'),('post',f'/api/results/{rid}/save'),('post',f'/api/results/{rid}/interpretations'),('get',f'/api/results/{rid}/messages')]:
   self.assertEqual(getattr(self.client,method)(path).status_code,404)
  self.assertEqual(self.client.get('/api/results').json(),[])
  self.assertEqual(self.client.post('/api/friends/feiyue/messages',json={'message':'hello','reading_id':rid}).status_code,404)
 def test_logout_origin_and_validation(self):
  self.assertEqual(self.client.post('/api/results/tarot',json={},headers={'Origin':'https://evil.example'}).status_code,403)
  self.assertEqual(self.client.post('/api/results/tarot',json={}).status_code,422)
  self.client.post('/api/logout');self.assertEqual(self.client.get('/api/export').status_code,401)
 def test_memory_permissions_pause_and_delete_vectors(self):
  m=self.client.post('/api/memories',json={'friend':'feiyue','content':'我正在准备面试'}).json()['id']
  owner=app.state.accounts.owner(self.client.cookies.get('buxi_session'))
  self.assertEqual(len(app.state.accounts.recall(owner,'feiyue','我正在准备面试')),1)
  self.assertEqual(app.state.accounts.recall(owner,'xingche','我正在准备面试'),[])
  self.client.put('/api/memories/'+m,json={'friend':'feiyue','content':'我正在准备面试','active':False})
  self.assertEqual(app.state.accounts.recall(owner,'feiyue','我正在准备面试'),[])
  self.client.post('/api/login',json={'code':self.codes[1]})
  self.assertEqual(self.client.get('/api/memories').json(),[])
  self.assertEqual(self.client.put('/api/memories/'+m,json={'friend':'feiyue','content':'hijack'}).status_code,404)
  self.client.delete('/api/memories/'+m)
  self.client.post('/api/login',json={'code':self.codes[0]});self.assertEqual(len(self.client.get('/api/memories').json()),1)
  self.client.delete('/api/memories/'+m)
  with app.state.store.connect() as db: self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0],0)
 def test_greeting_explicit_optin_once_and_cancel(self):
  self.assertIsNone(self.client.post('/api/greeting').json())
  self.client.put('/api/preferences',json={'greetings':True})
  self.assertIsNotNone(self.client.post('/api/greeting').json())
  self.assertIsNone(self.client.post('/api/greeting').json())
  self.client.put('/api/preferences',json={'greetings':False});self.assertIsNone(self.client.post('/api/greeting').json())
 def test_chat_uses_only_selected_scope(self):
  self.client.post('/api/memories',json={'friend':'feiyue','content':'我正在准备面试'})
  with patch.object(model,'complete',return_value='我们先看看你最在意哪一点。') as complete:
   self.assertEqual(self.client.post('/api/friends/feiyue/messages',json={'message':'我正在准备面试'}).status_code,200)
   self.assertIn('用户确认保存',complete.call_args.args[0][0]['content'])
   self.client.post('/api/friends/xingche/messages',json={'message':'你好'})
   self.assertNotIn('我正在准备面试',str(complete.call_args.args[0]))
 def test_reversals_and_sticks(self):
  self.assertFalse(any(c['reversed'] for c in self.draw(allow_reversed=False).json()['cards']))
  r=self.client.post('/api/results/sticks',json={'request_key':'stick-test-01'}).json()
  self.assertEqual(r['system'],'sticks');self.assertEqual(r['cards'][0]['kind'],'卜犀原创签')
 def test_knowledge_and_limit(self):
  rows=self.client.get('/api/knowledge',params={'q':'愚者'}).json()
  self.assertTrue(rows);self.assertEqual(rows[0]['card']['name'],'愚者')
  self.assertEqual(self.client.get('/api/knowledge',params={'q':'x'*201}).status_code,422)
 def test_login_cookie_and_rate_limit(self):
  r=self.client.post('/api/login',json={'code':self.codes[0]});self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertIn('SameSite=strict',r.headers['set-cookie'])
  for _ in range(11): r=self.client.post('/api/login',json={'code':'bad'})
  self.assertEqual(r.status_code,429)
 def test_temp_expiry(self):
  r=self.draw().json();r['created_at']='2000-01-01T00:00:00+00:00'
  with app.state.store.connect() as db: db.execute('UPDATE results SET content=? WHERE id=?',(json.dumps(r),r['id']))
  self.assertEqual(self.client.get('/api/results/'+r['id']).status_code,404)
