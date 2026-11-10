"""Offline structural/provenance validation. Does not grade interpretation quality."""
from pathlib import Path
import hashlib
import json

def validate():
    root=Path(__file__).resolve().parent
    doc=json.loads((root/'cards.json').read_text(encoding='utf-8'))
    cards=doc['cards']
    sources=json.loads((root/'sources.json').read_text(encoding='utf-8'))
    source_ids={s['id'] for s in sources}
    raw_bytes=(root/'sources/waite_pg43548.txt').read_bytes()
    raw=raw_bytes.decode('utf-8-sig').replace('\r\n','\n')
    lines=raw.splitlines()
    checks=[]
    def check(name,condition):
        checks.append({'check':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    expected={f'major-{i}' for i in range(22)}|{f'{s}-{i}' for s in ['wands','cups','swords','pentacles'] for i in range(1,15)}
    check('78 distinct expected RWS IDs',len(cards)==78 and {c['id'] for c in cards}==expected)
    check('source bytes SHA256',hashlib.sha256(raw_bytes).hexdigest()==sources[0]['raw_sha256'])
    check('RWS VIII=Strength XI=Justice',next(c for c in cards if c['id']=='major-8')['name_en']=='Strength' and next(c for c in cards if c['id']=='major-11')['name_en']=='Justice')
    for c in cards:
        check(c['id']+' human-review status honest',c['review']['human_reviewed'] is False)
        for direction in ['upright','reversed']:
            h=c['historical'][direction]
            check(c['id']+' '+direction+' fields',bool(h['summary_zh']) and bool(h['text_en']) and bool(c['editorial'][direction+'_zh']))
            check(c['id']+' '+direction+' evidence exists',h['evidence_key'] in c['evidence'])
        for key,e in c['evidence'].items():
            check(c['id']+' '+key+' source exists',e['source_id'] in source_ids)
            actual='\n'.join(lines[e['line_start']-1:e['line_end']]).strip()
            check(c['id']+' '+key+' exact source span',actual==e['text_en'])
            check(c['id']+' '+key+' excerpt hash',hashlib.sha256(actual.encode()).hexdigest()==e['excerpt_sha256'])
    chunks=[json.loads(x) for x in (root/'retrieval_chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    check('156 unique orientation chunks',len(chunks)==156 and len({c['chunk_id'] for c in chunks})==156)
    check('exactly two orientations per card',{(c['card_id'],c['orientation']) for c in chunks}=={(cid,o) for cid in expected for o in ['upright','reversed']})
    for ch in chunks:
        idx=int(ch['citation_path'].split('/')[2])
        check(ch['chunk_id']+' citation points to matching card',cards[idx]['id']==ch['card_id'])
        check(ch['chunk_id']+' adaptation labeled',ch['content_kind']=='project_adaptation' and ch['review_status']=='human_review_pending')
    two=next(c for c in cards if c['id']=='cups-2')
    check('Cups Two reversal is supplement not invented main entry',two['historical']['reversed']['evidence_key']=='reversal_supplement' and two['historical']['reversed']['text_en']=='Passion.')
    check('modern book bodies excluded',all(not s.get('used_for_card_meanings') for s in sources if s['id'] in ['pollack_78_wisdom_bibliography','greer_reversals_bibliography']))
    evals=[json.loads(x) for x in (root/'eval_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    check('20 eval specifications explicitly not run',len(evals)==20 and all(e['status']=='not_run' for e in evals))
    report={'knowledge_version':doc['knowledge_version'],'checked_on':'2026-11-10','card_count':len(cards),'chunk_count':len(chunks),'structural_checks':len(checks),'passed':all(c['passed'] for c in checks),'human_semantic_review':'not_done','application_integration':'not_done','live_model_evaluation':'not_run','meaning_of_pass':'数量、字段、引用定位和字节一致性通过；不是专业内容或预测有效性认证。','checks':checks}
    (root/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))

if __name__=='__main__':validate()
