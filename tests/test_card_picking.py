"""User-selected hidden decks: persistence, privacy and retry behavior."""
import concurrent.futures,json,random,unittest
from unittest.mock import patch
import test_api
from server.app.main import app
from server.app import model
from server.app.service import Store,Conflict
from server.app.tarot import shuffled_deck

class PickingTests(unittest.TestCase):
 setUp=test_api.ApiTests.setUp
 tearDown=test_api.ApiTests.tearDown
 def start(self,**kwargs):
  payload={'question':'先做哪件事？','spread':'three','request_key':'choose-cards-001','select_cards':True,'save':True,**kwargs}
  response=self.client.post('/api/results/tarot',json=payload)
  self.assertEqual(response.status_code,200,response.text)
  return response.json()
 def pick(self,r,slot,order):
  return self.client.post(f"/api/results/{r['id']}/picks",json={'slot':slot,'order':order})
 def test_frozen_deck_hidden_and_selected_positions_match(self):
  frozen=shuffled_deck(rng=random.Random(42))
  with patch('server.app.tarot.shuffled_deck',return_value=frozen) as shuffle:
   r=self.start();self.assertEqual(r,self.start());self.assertEqual(shuffle.call_count,1)
  self.assertEqual(r['cards'],[]);self.assertNotIn('knowledge_snapshot',r)
  self.assertNotIn('hidden_decks',self.client.get('/api/export').text)
  for order,slot in enumerate([77,3,26]):
   response=self.pick(r,slot,order)
   self.assertEqual(response.status_code,200)
   current=response.json()
   if order<2:self.assertEqual(current['cards'],[])
  self.assertEqual([c['id'] for c in current['cards']],[frozen[i]['id'] for i in [77,3,26]])
  self.assertEqual([c['reversed'] for c in current['cards']],[frozen[i]['reversed'] for i in [77,3,26]])
  self.assertEqual([c['position'] for c in current['cards']],['当下','值得留意','可以尝试'])
  self.assertEqual(len(current['knowledge_snapshot']),3)
  with app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM hidden_decks').fetchone()[0],0)
  with patch.object(model,'complete',return_value='先留意当下能做的一步。[K1]'):
   self.assertEqual(self.client.post(f"/api/results/{r['id']}/interpretations").status_code,200)
  c=self.client.post('/api/friends/feiyue/conversations',json={'reading_id':r['id']}).json()
  self.assertEqual(c['reading']['cards'],current['cards'])
 def test_response_loss_restart_and_conflicting_choices(self):
  r=self.start();a=self.pick(r,9,0)
  self.assertEqual(a.json(),self.pick(r,9,0).json())
  self.assertEqual(self.pick(r,8,0).status_code,409)
  self.assertEqual(self.pick(r,9,1).status_code,422)
  store=Store(app.state.store.path)
  owner=app.state.accounts.owner(self.client.cookies.get('buxi_session'))
  self.assertEqual(store.get(r['id'],owner)['selection']['picked'],[9])
  self.assertEqual(self.pick(r,8,1).status_code,200)
  self.assertEqual(self.pick(r,7,2).status_code,200)
  self.assertEqual(self.pick(r,7,2).status_code,200)
  self.assertEqual(self.pick(r,1,2).status_code,409)
  self.assertEqual(len(store.get(r['id'],owner)['cards']),3)
 def test_concurrent_picks_cannot_fill_two_positions(self):
  r=self.start();store=app.state.store
  owner=app.state.accounts.owner(self.client.cookies.get('buxi_session'))
  def choose(slot):
   try:store.pick(r['id'],slot,0,owner);return 'ok'
   except Conflict:return 'conflict'
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   outcomes=list(pool.map(choose,[5,17]))
  self.assertEqual(sorted(outcomes),['conflict','ok'])
  self.assertEqual(len(store.get(r['id'],owner)['selection']['picked']),1)
 def test_pending_blocks_interpret_and_chat_and_enforces_owner(self):
  r=self.start()
  with patch.object(model,'complete') as call:
   self.assertEqual(self.client.post(f"/api/results/{r['id']}/interpretations").status_code,409)
   self.assertEqual(self.client.post('/api/friends/feiyue/conversations',json={'reading_id':r['id']}).status_code,409)
   self.assertEqual(self.client.post('/api/friends/feiyue/messages',json={'reading_id':r['id'],'message':'继续'}).status_code,409)
   call.assert_not_called()
  self.assertEqual(self.pick(r,78,0).status_code,422)
  self.client.post('/api/login',json={'code':self.codes[1]})
  self.assertEqual(self.pick(r,1,0).status_code,404)
 def test_expiry_and_delete_remove_hidden_cards(self):
  r=self.start(save=False)
  with app.state.store.connect() as db:
   r['created_at']='2000-01-01T00:00:00+00:00'
   db.execute('UPDATE results SET content=? WHERE id=?',(json.dumps(r),r['id']))
  self.assertEqual(self.pick(r,1,0).status_code,410)
  second=self.start(request_key='choose-cards-002')
  self.client.delete('/api/results/'+second['id'])
  self.assertEqual(self.pick(second,1,0).status_code,410)
  with app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM hidden_decks').fetchone()[0],0)
 def test_single_card_and_no_reversals(self):
  frozen=shuffled_deck(False,random.Random(8))
  self.assertEqual(len({c['id'] for c in frozen}),78)
  self.assertTrue(all(not c['reversed'] for c in frozen))
  r=self.start(spread='single',allow_reversed=False)
  final=self.pick(r,23,0).json()
  self.assertEqual(final['selection']['status'],'complete')
  self.assertFalse(final['cards'][0]['reversed'])
  self.assertEqual(final['cards'][0]['position'],'此刻的提醒')
