"""Read pinned upstream sources, record hashes/metadata, never update vendored data."""
import hashlib, json, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REPOS = {'python-tarot':'jeremytarling/python-tarot', 'tarotoo':'Tarotoo-com/tarotoo-tarot-dataset', 'ts-tarot-cards':'infomofo/ts-tarot-cards'}

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Buxi-source-audit'}), timeout=30).read()

def main():
    revisions=json.loads((ROOT/'server/app/data/sources.json').read_text('utf-8'))
    report=[]
    for key, repo in REPOS.items():
        rev=revisions[key]
        record={'id':key,'author':repo.split('/')[0],'title':repo.split('/')[1], 'revision':rev,'accessed_on':'2026-11-11','url':'https://github.com/'+repo,'files':[],'use':'reference_only; no new source or images copied'}
        try:
            tree=json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/{rev}?recursive=1'))['tree']
            paths=[x['path'] for x in tree if x['type']=='blob']
            record['license_files']=[p for p in paths if 'license' in p.lower() or 'copying' in p.lower()]
            selected=[p for p in paths if p.lower().startswith('readme') or p in record['license_files']]
            if key=='python-tarot': selected += [p for p in paths if p.endswith('cards.py')]
            elif key=='tarotoo': selected += [p for p in paths if p.endswith('.json') and 'package' not in p][:2]
            else: selected += [p for p in paths if p.endswith('.ts') and any(t in p.lower() for t in ['card','spread','suit','arcana'])][:7]
            for p in selected:
                url=f'https://raw.githubusercontent.com/{repo}/{rev}/{p}'
                raw=fetch(url); text=raw.decode('utf-8-sig')
                record['files'].append({'path':p,'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
                print('\n'+key+' '+p+'\n'+text[:14000])
                if key=='tarotoo' and p=='data/cards.json':
                    try: record['matches_local_data']=json.loads(text)==json.loads((ROOT/'server/app/data/tarotoo.json').read_text('utf-8'))
                    except ValueError: pass
            record['status']='opened_pinned_files'
        except Exception as exc: record.update(status='blocked',error=type(exc).__name__)
        report.append(record)
    out=ROOT/'docs/source-audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
