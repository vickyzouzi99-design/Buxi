import concurrent.futures
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server.app.tarot import deck, draw
from server.app.service import Store, Conflict
from server.app import model

class TarotTests(unittest.TestCase):
    def test_full_deck(self):
        self.assertEqual(len(deck()),78)
        self.assertEqual(len({c["id"] for c in deck()}),78)
    def test_seeded_draw_and_unique_positions(self):
        a=draw("three",random.Random(10))
        self.assertEqual(a,draw("three",random.Random(10)))
        self.assertEqual(len({c["id"] for c in a}),3)
        self.assertEqual([c["position"] for c in a],["当下","值得留意","可以尝试"])
    def test_invalid_spread(self):
        with self.assertRaises(ValueError): draw("fake")
    def test_both_orientations_possible(self):
        orientations={c["reversed"] for i in range(30) for c in draw("single",random.Random(i))}
        self.assertEqual(orientations,{False,True})

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"test.db"
        self.db=Store(self.path)
    def tearDown(self): self.temp.cleanup()
    def create(self): return self.db.create("面试有点紧张","three","request-0001")
    def test_retry_and_restart(self):
        first=self.create()
        again=Store(self.path).create("面试有点紧张","three","request-0001")
        self.assertEqual(first,again)
        self.assertEqual(len(self.db.list()),1)
    def test_conflicting_retry(self):
        self.create()
        with self.assertRaises(Conflict): self.db.create("不同的问题","three","request-0001")
    def test_concurrent_requests_draw_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            results=list(pool.map(lambda _:self.create(),range(5)))
        self.assertEqual(len({r["id"] for r in results}),1)
        self.assertEqual(len(self.db.list()),1)
    def test_owner_scope(self):
        result=self.create()
        with self.assertRaises(KeyError): self.db.get(result["id"],"other")
        self.assertEqual(self.db.list("other"),[])
        with self.assertRaises(KeyError): self.db.delete(result["id"],"other")
    def test_reinterpretation_preserves_cards(self):
        first=self.create()
        updated=self.db.set_interpretation(first["id"],"新的解释","test-model")
        self.assertEqual(first["cards"],updated["cards"])
        self.assertEqual(first["id"],updated["id"])
        self.assertEqual(updated["interpretation_source"],"ai")
    def test_delete_cascades_messages(self):
        r=self.create()
        self.db.add_exchange(r["id"],"hello","world")
        self.assertEqual(len(self.db.messages(r["id"])),2)
        self.db.delete(r["id"])
        self.assertEqual(self.db.list(),[])
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],0)
    def test_unconfigured_model_does_not_fake_response(self):
        with patch.dict("os.environ",{"MODEL_API_KEY":"","MODEL_NAME":""}):
            with self.assertRaises(model.ModelError): model.interpret(self.create())
    def test_failed_model_preserves_result(self):
        r=self.create()
        with patch.object(model,"complete",side_effect=model.ModelError("offline")):
            with self.assertRaises(model.ModelError): model.interpret(r)
        self.assertEqual(self.db.get(r["id"]),r)

if __name__=="__main__": unittest.main()
