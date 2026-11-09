"""Build public-source smoke-test SFT pairs, never read users or their messages.
78 card identities partitioned before making upright/reversed examples.
These English source summaries test the pipeline, not Chinese dialogue quality.
"""
import json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prepare(destination):
 cards=json.loads((ROOT/'server/app/data/tarotoo.json').read_text());ids=list(range(78));random.Random(42).shuffle(ids);held=set(ids[:12])
 destination.mkdir(parents=True,exist_ok=True)
 sets={'train':[],'eval':[]}
 for c in cards:
  for orientation in ['upright','reversed']:
   row={'card_id':c['id'],'source':'Tarotoo MIT','messages':[
    {'role':'system','content':'Explain the supplied tarot symbolism briefly. This is reflection, not a factual prediction. Use only the supplied source.'},
    {'role':'user','content':f"Card: {c['name']}. Orientation: {orientation}. Position: reflection. Source: {c['meaning_'+orientation]}"},
    {'role':'assistant','content':f"As a reflection, this card can suggest: {c['meaning_'+orientation]}"}]}
   sets['eval' if c['id'] in held else 'train'].append(row)
 for split,rows in sets.items(): (destination/(split+'.jsonl')).write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n')
 return {k:len(v) for k,v in sets.items()}
if __name__=='__main__': print(prepare(ROOT/'training/data'))
