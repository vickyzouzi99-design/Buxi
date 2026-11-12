"""Versioned, read-only public knowledge. No user content or model tool writes.

Known cards use exact IDs; general queries use names and lexical keywords, not embeddings.
The supplied package is retained intact as the immutable v0.1 source branch.
"""
from copy import deepcopy
import json
import re
from .policies import POLICY_VERSION, PROMPT_VERSION
from .personas import PERSONA_VERSION
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / 'Buxi_Tarot_Knowledge_v01'
_DATA = json.loads((PACKAGE / 'cards.json').read_text('utf-8'))
VERSION = _DATA['knowledge_version']
_CARDS = {c['id']:c for c in _DATA['cards']}
_SOURCES = {s['id']:s for s in json.loads((PACKAGE/'sources.json').read_text('utf-8'))}
_CHUNKS = [json.loads(s) for s in (PACKAGE/'retrieval_chunks.jsonl').read_text('utf-8').splitlines() if s.strip()]



INDEX_VERSION = 'names-keywords-v1:' + VERSION
ADAPTER_VERSION = 'knowledge-adapter-2026-11-11.1'

def exact(card_id, orientation, version=VERSION, historical=False):
    if version != VERSION: raise ValueError('此知识版本不可用；不会静默替换为新版')
    if orientation not in ('upright','reversed'): raise ValueError('未知方向')
    if card_id not in _CARDS: raise KeyError('本牌组没有此卡牌')
    c=_CARDS[card_id]; e=c['editorial']; h=c['historical']
    keys=list(e['basis_evidence_keys'])
    if h[orientation].get('evidence_key') not in keys: keys.append(h[orientation]['evidence_key'])
    evidence=[dict(c['evidence'][k], source_url=_SOURCES[c['evidence'][k]['source_id']]['url']) for k in keys]
    item={'entry_id':f'{card_id}:{orientation}:{version}'+(':historical' if historical else ''),
          'card_id':card_id,'name':c['name_zh'],'orientation':orientation,'knowledge_version':version,
          'content_kind':'historical_summary' if historical else 'project_adaptation',
          'review_status':'human_review_pending', 'source_id':'waite_pg43548_1918' if historical else 'buxi_editorial_v01',
          'title':c['name_zh']+(' 正位' if orientation=='upright' else ' 逆位'),
          'text':h[orientation]['summary_zh'] if historical else e[orientation+'_zh'],
          'caution':e['caution_zh'],'attribution':h['note'] if historical else e['attribution_label'],
          'edition_note':_SOURCES['waite_pg43548_1918']['edition_note'],
          'evidence':evidence,'symbolism':h.get('symbolism',{}).get('summary_zh','')}
    if historical: item['text_en']=h[orientation]['text_en']
    item['adapter_version']=ADAPTER_VERSION
    if card_id=='major-13':
        item['symbolism']=''
        item['review_note']='原包“黑色玫瑰旗”易误读为黑玫瑰。当前不向模型提供该中文图像描述；可核对英文黑旗与神秘玫瑰的原始片段。'
    return deepcopy(item)

def snapshot(cards):
    return [exact(c['id'],'reversed' if c['reversed'] else 'upright') for c in cards]

def is_historical(query):
    return any(x in query.lower() for x in ('原文','历史','词表','waite','伟特','1918','1910','出处','象征','图案','图像'))

def search(query, version=VERSION):
    if version != VERSION: raise ValueError('未找到请求的知识版本')
    q=query.lower().strip()
    if not q: return []
    named=[c for c in _CARDS.values() if re.search(r'(?<![a-z0-9-])'+re.escape(c['id'])+r'(?![0-9])',q) or any(n.lower() in q for n in [c['name_zh'],c['name_en'],*c['aliases']] if n)]
    orientations=['reversed'] if '逆位' in q and '正位' not in q else ['upright'] if '正位' in q and '逆位' not in q else ['upright','reversed']
    output=[]
    if named:
        for c in named[:8]:
            for o in orientations: output.append(exact(c['id'],o,historical=is_historical(q)))
    elif any(x in q for x in ('塔罗','牌义','象征','权杖','圣杯','宝剑','星币')):
        # Intent gate prevents irrelevant fragments from being inserted into daily chat.
        scored=[]
        for c in _CARDS.values():
            score=sum(len(k) for k in c['editorial']['keywords_zh'] if k in q)
            if score: scored.append((score,c))
        scored.sort(key=lambda x:-x[0])
        for _,c in scored[:min(6,max(2,len(q)//12))]:
            for o in orientations: output.append(exact(c['id'],o,historical=is_historical(q)))
    if any(x in q for x in ('牌阵','牌位','单牌','三牌','阻碍位')):
        from .rules import SPREAD_DEFINITIONS, SPREAD_VERSION
        output.append({'entry_id':'spreads:'+SPREAD_VERSION,'title':'卜犀项目牌阵与牌位', 'text':json.dumps(SPREAD_DEFINITIONS,ensure_ascii=False),'source_id':'buxi_spreads','knowledge_version':SPREAD_VERSION,'content_kind':'project_rule','review_status':'project_defined','evidence':[]})
    if any(x in q for x in ('逆位怎么','逆位方法','解释方法','解读规则','逆位一定','逆位都','50%','概率')):
        output.append({'entry_id':'policy:'+POLICY_VERSION,'title':'卜犀解释规则','text':'逐牌读取正逆位，不一律视作负面或正位反义。正逆各50%是抽牌程序规则，不是现实概率或预测准确率。资料缺失时说明不足；情境推测和来源解释分开。','source_id':'buxi_policy','knowledge_version':POLICY_VERSION,'content_kind':'project_rule','review_status':'project_defined','evidence':[]})
    return output

def references(result=None, query=''):
    items=deepcopy((result or {}).get('knowledge_snapshot',[]))
    if result and result.get('system')=='sticks':
        # Keep the original in-product text available to interpretation and follow-ups.
        # This is a saved original prompt, not a traditional temple signbook.
        for c in result['cards']:
            items.append({'entry_id':f"original-stick:{result['id']}:{c['id']}",'card_id':c['id'],
                          'title':c['name'],'text':c['prompt'],'source_id':'buxi_original_sticks',
                          'knowledge_version':'embedded-original-stick','content_kind':'project_original',
                          'review_status':'project_defined','evidence':[]})
    # Old records retain their embedded Tarotoo meanings; never apply the new default to them.
    if result and result.get('system')=='tarot' and not items:
        for c in result['cards']:
            s=c.get('source',{})
            items.append({'entry_id':f"legacy:{c['id']}:{s.get('revision','unknown')}",'card_id':c['id'],'title':c['name'], 'orientation':'reversed' if c['reversed'] else 'upright','text':c['prompt'],'source_id':'tarotoo','knowledge_version':s.get('revision','legacy'),'content_kind':'legacy_source_text','review_status':'human_review_pending','evidence':[{'source_url':s.get('url',''),'section':'card '+str(s.get('id',''))}]})
        return label(items)
    if query:
        extra=search(query)
        # Explicit historical query receives history for the actual spread too.
        if result and is_historical(query):
            extra += [exact(c['id'],'reversed' if c['reversed'] else 'upright',result['knowledge_version'],True) for c in result['cards'] if result.get('system')=='tarot']
        items += extra
    unique={x['entry_id']:x for x in items}
    return label(list(unique.values()))

def label(items):
    return [dict(x,citation_id=f'K{i+1}') for i,x in enumerate(items)]

def selected_citations(text, supplied):
    known={x['citation_id']:x for x in supplied}
    used=set(re.findall(r'\[(K\d+)\]',text))
    if used-set(known): raise ValueError('回答引用了本次未提供的资料，请重试')
    return [x for k,x in known.items() if k in used]

def public_hits(query):
    return [{'card':{'id':r['entry_id'],'name':r['title'],'prompt':r['text']},'reference':r,'method':INDEX_VERSION} for r in search(query)]
