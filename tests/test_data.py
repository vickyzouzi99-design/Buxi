import unittest,json,importlib.util,tempfile
from pathlib import Path
from server.app.tarot import deck
ROOT=Path(__file__).resolve().parents[1]
class DataTests(unittest.TestCase):
 def test_sources_and_different_minor_meanings(self):
  cards=deck();self.assertEqual(len({c['source']['id'] for c in cards}),78)
  for c in cards:
   self.assertTrue(c['meanings']['upright']);self.assertTrue(c['meanings']['reversed']);self.assertEqual(len(c['source']['revision']),40)
  lookup={c['id']:c for c in cards};self.assertNotEqual(lookup['cups-1']['prompt'],lookup['cups-10']['prompt'])
 def test_training_card_groups_separate(self):
  spec=importlib.util.spec_from_file_location('prepare',ROOT/'training/prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as d:
   counts=module.prepare(Path(d));self.assertEqual(counts,{'train':132,'eval':24})
   groups=[{json.loads(x)['card_id'] for x in (Path(d)/(name+'.jsonl')).read_text().splitlines()} for name in ['train','eval']]
   self.assertFalse(groups[0]&groups[1]);self.assertEqual(len(groups[0]|groups[1]),78)
 def test_prebuilt_asset_matches_source(self):
  self.assertEqual((ROOT/'web/public/assets/card-back.png').read_bytes(),(ROOT/'web/dist/assets/card-back.png').read_bytes())
