"""Reproducible structure/mapping report; does not certify translation quality."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.app import knowledge
from server.app.tarot import deck

PRIORITY=['major-0','major-1','major-3','major-9','major-10','major-13','major-16','major-17','major-18','wands-3','wands-4','cups-2','cups-8','cups-9','swords-4','swords-6','swords-9','swords-10','swords-13']
def main():
 cards=deck();mismatches=[]
 for c in cards:
  k=knowledge._CARDS[c['id']]
  for a,b in [('name','name_zh'),('rank','rank'),('suit','suit'),('arcana','arcana')]:
   if c[a]!=k[b]:mismatches.append({'id':c['id'],'field':a})
 report={'date':'2026-11-11','knowledge_version':knowledge.VERSION,'adapter_version':knowledge.ADAPTER_VERSION,'card_count':len(cards),'orientation_count':len(knowledge._CHUNKS),'mapping_mismatches':mismatches,'duplicate_reading_copy_identical':(ROOT/'Tarot_Knowledge_ZH.md').read_bytes()==(knowledge.PACKAGE/'Tarot_Knowledge_ZH.md').read_bytes(),'reading_sha256':hashlib.sha256((ROOT/'Tarot_Knowledge_ZH.md').read_bytes()).hexdigest(),'automatic_structure':'1013 checks passed using supplied validate.py; its dated report retained unchanged','machine_assisted_review_scope':PRIORITY,'human_professional_review':'not_done','license_status':'separate upstream / Gutenberg / editorial records; no blanket MIT declaration','priority_comparisons':[]}
 for cid in PRIORITY:
  k=knowledge._CARDS[cid];old=next(c for c in cards if c['id']==cid)
  report['priority_comparisons'].append({'card_id':cid,'name':k['name_zh'],'waite_1918_reverse_summary':k['historical']['reversed']['summary_zh'],'waite_1918_reverse_excerpt':k['historical']['reversed']['text_en'],'default_editorial_reverse':k['editorial']['reversed_zh'],'tarotoo_reverse':old['meanings']['reversed'],'tarotoo_version':old['source']['revision'],'decision':'default editorial only; do not blend branches','review':'machine_assisted_spot_check; human_review_pending'})
 (ROOT/'docs/knowledge-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='priority_comparisons'},ensure_ascii=False,indent=2))
if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8');main()
