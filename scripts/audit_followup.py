"""Targeted verification, no dependency upgrades or vendored file changes."""
import json,sys
from audit_sources import ROOT,fetch
sys.stdout.reconfigure(encoding='utf-8')
p=ROOT/'docs/source-audit.json';records=json.loads(p.read_text('utf-8'))
for r in records:
 if r['id']=='tarotoo':
  data=json.loads(fetch(next(x['url'] for x in r['files'] if x['path']=='data/cards.json')))
  local=json.loads((ROOT/'server/app/data/tarotoo.json').read_text('utf-8'))
  r['matches_local_data']=data==local
  r['license']='MIT; see pinned LICENSE and licenses/Tarotoo-MIT.txt'
 elif r['id']=='python-tarot':
  r['license']='README permits code reuse; interpretations CC BY-NC-SA; image permission personal to upstream. None newly copied.'
 elif r['id']=='ts-tarot-cards':
  text=fetch(next(x['url'] for x in r['files'] if x['path']=='README.md')).decode('utf-8')
  i=text.find('## License');print('Pinned ts-tarot-cards license section:',text[i:i+180])
  r['license']='README states ISC; no standalone LICENSE in pinned tree; reference structure only'
print('Tarotoo pinned canonical data matches:',next(r for r in records if r['id']=='tarotoo')['matches_local_data'])
p.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
