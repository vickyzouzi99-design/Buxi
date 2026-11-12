import React,{useEffect,useState} from 'react';
import type {Selection} from './types';

export function CardPicker({selection,busy,onPick,onRecover}:{selection:Selection;busy:boolean;onPick:(slot:number)=>void;onRecover:()=>void}){
 const [shuffling,setShuffling]=useState(selection.picked.length===0);
 useEffect(()=>{
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){setShuffling(false);return}
  const timer=setTimeout(()=>setShuffling(false),800);
  return()=>clearTimeout(timer);
 },[]);
 return <section className="pick-ritual" aria-label="亲手选牌" aria-busy={busy}>
  <div className="pick-heading" aria-live="polite">
   <span className="eyebrow">A MOMENT OF INTUITION</span>
   <h2>{shuffling?'让牌轻轻散开…':`选一张，留给「${selection.positions[selection.picked.length]}」`}</h2>
   <p>{shuffling?'慢慢呼吸，想着此刻的问题。':'轻触一张让你想停留的牌。向下滑动，还可以看看更多。'}</p>
  </div>
  <ol className="picked-places">{selection.positions.map((name,i)=><li key={name} className={i<selection.picked.length?'chosen':i===selection.picked.length?'current':''}>
   <span aria-hidden="true">{i<selection.picked.length?'✦':i+1}</span>
   <b>{name}</b><small>{i<selection.picked.length?'已选好':i===selection.picked.length?'等你选择':'稍后选择'}</small>
  </li>)}</ol>
  {shuffling?<div className="shuffle-stage" aria-hidden="true"><i/><i/><i/></div>:<div className="pick-field" tabIndex={0} aria-label="牌堆，可滚动查看全部卡牌">
   <div className="pick-grid">{Array.from({length:selection.total},(_,slot)=>{
    const chosen=selection.picked.includes(slot);
    return <button key={slot} type="button" className={'pick-card'+(chosen?' chosen':'')} disabled={busy||chosen}
     aria-label={`第${slot+1}张背面牌${chosen?'，已选':''}`} aria-pressed={chosen} onClick={()=>onPick(slot)}>
     {chosen&&<span aria-hidden="true">✦</span>}
    </button>;
   })}</div>
  </div>}
  <p className="pick-progress" role="status">{busy?'正在收好这张牌…':`已选 ${selection.picked.length} / ${selection.positions.length} 张`}</p>
  <div className="center"><button type="button" className="text-button" disabled={busy||shuffling} onClick={onRecover}>恢复选牌进度</button></div>
 </section>;
}
