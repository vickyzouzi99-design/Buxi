import React from 'react';
import type {Reference} from './types';
const kindLabels:Record<string,string>={
 project_adaptation:'卜犀反思式改写',
 historical_summary:'历史资料 · 中文摘要',
 project_rule:'项目规则',
 project_original:'卜犀原创反思内容',
};

export function Sources({items=[]}:{items?:Reference[]}){
 if(!items.length)return null;
 return <details className="sources">
  <summary>资料依据 · {items.length} 条</summary>
  <p>塔罗资料为中文编辑初稿，待专业审核。可以在这里查看本次解读参考的内容与来源。</p>
  {items.map(r=><article key={r.entry_id}>
   <b>{r.citation_id&&`[${r.citation_id}] `}{r.title}</b>
   <p>{kindLabels[r.content_kind]||'历史版本资料'} · {r.source_id}<br/>版本 {r.knowledge_version}</p>
   <p>{r.text}</p>
   {r.caution&&<p>{r.caution}</p>}
   {r.edition_note&&<p>{r.edition_note}</p>}
   {r.evidence.map((e,i)=><details key={i}>
    <summary>{e.section||'来源'}{e.line_start?` · 本地转录行 ${e.line_start}–${e.line_end}`:''}</summary>
    {e.source_url&&<a href={e.source_url} target="_blank" rel="noreferrer">打开来源 ↗</a>}
    {e.text_en&&<p className="prose">{e.text_en}</p>}
   </details>)}
  </article>)}
 </details>;
}
