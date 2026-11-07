import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Card = { id: string, name: string, position: string, reversed: boolean, prompt: string, kind: string };
type Reading = { id: string, question: string, spread: string, cards: Card[], created_at: string, interpretation: string, interpretation_source: string };
type Message = { role: string, content: string };
const nav = [['home', '⌂', '今日'], ['explore', '✧', '探索'], ['friends', '☏', '朋友'], ['records', '▤', '我的记录']];
async function api(path: string, body?: unknown, method?: string) {
  const res = await fetch(path, { method: method || (body ? 'POST' : 'GET'), headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求未完成，请检查输入后重试。');
  return data;
}
function Emblem({ small = false }: { small?: boolean }) {
  return <svg className={small ? 'emblem small' : 'emblem'} viewBox="0 0 240 240" fill="none" aria-hidden="true">
    <circle cx="120" cy="120" r="83" stroke="currentColor" strokeWidth="1" />
    <circle cx="120" cy="120" r="69" stroke="currentColor" strokeWidth=".5" strokeDasharray="2 6" />
    {Array.from({ length: 12 }, (_, i) => <path key={i} d="M120 18v16" stroke="currentColor" transform={'rotate(' + i * 30 + ' 120 120)'} />)}
    <path d="M120 65c3 36 19 52 55 55-36 3-52 19-55 55-3-36-19-52-55-55 36-3 52-19 55-55Z" stroke="currentColor" />
    <circle cx="120" cy="120" r="13" stroke="currentColor" /><path d="M74 171c25 11 56 11 81-1" stroke="currentColor" />
    <circle cx="185" cy="48" r="3" fill="currentColor" /><circle cx="42" cy="175" r="2" fill="currentColor" />
  </svg>
}
function App() {
  const [page, setPage] = useState('home'), [question, setQuestion] = useState(''), [spread, setSpread] = useState('three');
  const [reading, setReading] = useState<Reading | null>(null), [records, setRecords] = useState<Reading[]>([]);
  const [revealed, setRevealed] = useState(false), [busy, setBusy] = useState(''), [error, setError] = useState('');
  const [status, setStatus] = useState<{ model_configured: boolean } | null>(null), [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState(''), [showChat, setShowChat] = useState(false);
  const [requestKey, setRequestKey] = useState<string | null>(null);
  useEffect(() => { api('/api/status').then(setStatus).catch(() => setError('暂时连不上本地服务，请确认后端已启动。')); refresh() }, []);
  function refresh() { api('/api/results').then(setRecords).catch(() => { }); }
  function go(next: string) { setPage(next); setError(''); setShowChat(false); }
  async function run(name: string, fn: () => Promise<void>) { if (busy) return; setBusy(name); setError(''); try { await fn() } catch (e) { setError((e as Error).message) } finally { setBusy('') } }
  function changeQuestion(v: string) { setQuestion(v); setRequestKey(null) }
  async function draw() {
    const key = requestKey || crypto.randomUUID(); setRequestKey(key);
    await run('draw', async () => {
      const r = await api('/api/results/tarot', { question, spread, request_key: key });
      setReading(r); setRevealed(false); setMessages([]); setShowChat(false); setPage('tarot'); refresh()
    })
  }
  async function openRecord(r: Reading) {
    setReading(r); setRevealed(true); setPage('tarot'); setShowChat(false); setError('');
    try { setMessages(await api('/api/results/' + r.id + '/messages')) } catch { setMessages([]) }
  }
  async function chat() {
    if (!reading || !draft.trim()) return;
    const text = draft.trim();
    await run('chat', async () => {
      const reply = await api('/api/results/' + reading.id + '/messages', { message: text });
      setMessages(m => [...m, { role: 'user', content: text }, reply]); setDraft('')
    })
  }
  const tools = [{ symbol: '☉', name: '星盘', en: 'ASTROLOGY', desc: '从星辰的位置，认识自己的不同面。', ready: false },
  { symbol: '✦', name: '塔罗', en: 'TAROT', desc: '翻开一张牌，让心里的线索慢慢浮现。', ready: true },
  { symbol: '☷', name: '易经', en: 'I CHING', desc: '观象与变化，换个角度看当下。', ready: false },
  { symbol: '〰', name: '灵签', en: 'FORTUNE STICKS', desc: '轻轻摇一支签，留一点偶然的启发。', ready: false }];
  const toolGrid = <div className="tool-grid">{tools.map(t => <button key={t.en} className={'tool ' + (t.ready ? 'ready' : '')} disabled={!t.ready || !!busy} onClick={() => { setReading(null); setRequestKey(null); go('tarot') }}>
    <span className="tool-symbol">{t.symbol}</span><span className="eyebrow">{t.en}</span><h3>{t.name}</h3><p>{t.desc}</p><span className="tool-link">{t.ready ? '开始探索 ↗' : '即将开放'}</span></button>)}</div>;
  return <div className="app">
    <aside><a className="brand" href="#" onClick={e => { e.preventDefault(); go('home') }}><span className="brand-symbol">卜</span><span>卜犀 <b>Buxi</b></span></a>
      <p className="side-caption">一点启发，一点陪伴。</p><nav aria-label="主要导航">{nav.map(([id, icon, title]) => <button key={id} className={page === id || (id === 'explore' && page === 'tarot') ? 'active' : ''} onClick={() => go(id)} disabled={!!busy}><span>{icon}</span>{title}<i>·</i></button>)}</nav>
      <div className="side-bottom"><span className="status-dot" />自己的小小天地<p>本地个人版 · M0 / M1</p><small>仅供娱乐与自我探索</small></div></aside>
    <main><header><span>{new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())}</span><span className="top-note">慢一点，也没关系 <span className="avatar">B</span></span></header>
      {error && <div className="error" role="alert">{error}<button onClick={() => setError('')} aria-label="关闭提示">×</button></div>}
      {(page === 'home' || page === 'explore') && <>
        {page === 'home' ? <section className="hero"><div><span className="eyebrow">A LITTLE INSIGHT. A LITTLE COMPANY.</span><h1>给心事，<br />一点新的回声。</h1><p>看盘、抽牌、摇签。<br />也可以，只是找个朋友聊聊。</p><button className="primary" onClick={() => { setReading(null); setSpread('single'); setRequestKey(null); go('tarot') }}>抽一张牌 <span>↗</span></button><span className="hero-note">不急着寻找答案，先听听自己的声音。</span></div><div className="hero-art"><Emblem /><span>AS ABOVE, SO WITHIN</span></div></section>
          : <section className="page-heading"><span className="eyebrow">A MOMENT FOR YOURSELF</span><h1>从好奇开始。</h1><p>选一种喜欢的方式，探索此刻的心情。</p></section>}
        <div className="section-heading"><h2>给自己一点启发</h2><span>四种入口，同一个你</span></div>{toolGrid}
        {page === 'home' && <div className="home-bottom"><section className="daily"><span className="eyebrow">TODAY'S PAUSE · 今日小停顿</span><h2>先把注意力，还给自己。</h2><p>今天有没有一件小事，值得你对自己说声“做得不错”？</p><small>编辑精选反思提示 · 今日星象与个性化运势尚未开放</small></section><section className="friend-peek"><span className="friend-icon">☾</span><div><h3>绯月在这里</h3><p>抽完牌，我们可以接着聊。</p><button className="text-button" onClick={() => go('friends')}>认识朋友 ↗</button></div></section></div>}
      </>}
      {page === 'tarot' && <><button className="text-button back" disabled={!!busy} onClick={() => go('explore')}>← 返回探索</button>
        <section className="page-heading"><span className="eyebrow">TAROT · 一场与自己的对话</span><h1>{reading ? '让牌面，慢慢说。' : '把此刻的心事，放在这里。'}</h1><p>{reading ? reading.question || '这一次，为此刻的自己。' : '不必问得完美。一个念头，一种感受，都可以。'}</p></section>
        {!reading ? <div className="draw-layout"><section className="draw-form"><label htmlFor="question">你想聊些什么？<small>选填</small></label><textarea id="question" value={question} onChange={e => changeQuestion(e.target.value)} maxLength={1000} placeholder="最近，有什么事让你有点在意……" disabled={!!busy} /><div className="spread-options">{[['single', '一张牌', '此刻的提醒'], ['three', '三张牌', '当下 · 值得留意 · 可以尝试']].map(([value, label, desc]) => <button key={value} aria-pressed={spread === value} className={spread === value ? 'selected' : ''} disabled={!!busy} onClick={() => { setSpread(value); setRequestKey(null) }}><strong>{label}</strong><span>{desc}</span></button>)}</div><button className="primary" disabled={!!busy} onClick={draw}>{busy === 'draw' ? '正在抽取…' : '准备好了，抽牌 ↗'}</button><p className="fine">78 张牌 · 包含正逆位 · 抽取后自动保存<br />牌面是一种象征，不是对未来的承诺。</p></section><div className="deck-display"><div className="decor-card rear" /><div className="decor-card"><Emblem small /><span>BUXI · TAROT</span></div></div></div>
          : <><div className={'cards count-' + reading.cards.length}>{reading.cards.map((card, i) => <button className={'tarot-card ' + (revealed ? 'revealed' : '')} key={card.id} onClick={() => setRevealed(true)} aria-label={revealed ? card.name + ' ' + (card.reversed ? '逆位' : '正位') : '翻开牌面'}><span className="position">{card.position}</span><Emblem small /><strong>{revealed ? card.name : '卜犀'}</strong><span>{revealed ? (card.reversed ? '逆位 · REVERSED' : '正位 · UPRIGHT') : '点击翻开'}</span><small>{revealed ? card.kind : 'A MOMENT OF WONDER'}</small></button>)}</div>
            {!revealed && <p className="center fine">牌已经抽好并保存。轻触任意一张，一起揭晓。</p>}
            {revealed && <><section className="interpretation"><div className="section-heading"><h2>{reading.interpretation_source === 'ai' ? '给你的解读' : '给你的反思提示'}</h2><span>{reading.interpretation_source === 'ai' ? 'AI 生成' : '本地原创提示 · 非 AI 解读'}</span></div><div className="prose">{reading.interpretation}</div><div className="actions"><button className="primary" disabled={!!busy} onClick={() => run('interpret', async () => { setReading(await api('/api/results/' + reading.id + '/interpretations', {})); refresh() })}>{busy === 'interpret' ? '绯月正在读牌…' : reading.interpretation_source === 'ai' ? '重新解读这组牌' : '请 AI 解读 ↗'}</button><button className="secondary" disabled={!!busy} onClick={() => setShowChat(!showChat)}>{showChat ? '收起聊天' : '找绯月聊聊'}</button></div>{status && !status.model_configured && <p className="fine">模型尚未配置。你仍可抽牌、保存与阅读本地提示；AI 解读和聊天暂不可用。</p>}<details><summary>查看牌面依据与记录</summary><p>记录：{reading.id}<br />时间：{new Date(reading.created_at).toLocaleString()}<br />算法：tarot-78-v1 · 代码随机抽取，无放回。解读重试不会重新抽牌。</p></details></section>
              {showChat && <section className="chat"><h2>☾ 和绯月聊聊</h2><p className="fine">这段对话只围绕上面的牌阵。跨会话记忆与群聊尚未开放。</p><div className="messages" aria-live="polite">{messages.length === 0 && <p className="empty">可以从“这张牌让我想到……”开始。</p>}{messages.map((m, i) => <div key={i} className={'message ' + m.role}><small>{m.role === 'user' ? '你' : '绯月 · AI'}</small><p>
                {m.role === 'assistant'
                  ? m.content.split(/(\*\*[^*\n]+\*\*)/g).map((part, i) =>
                    i % 2 === 1
                      ? <strong key={i}>{part.slice(2, -2)}</strong>
                      : <span key={i}>{part}</span>
                  )
                  : m.content}
              </p></div>)}</div><form onSubmit={e => { e.preventDefault(); chat() }}><textarea aria-label="发送给绯月的消息" placeholder="说说你的想法…" value={draft} onChange={e => setDraft(e.target.value)} maxLength={2000} disabled={!!busy} /><button className="primary" disabled={!!busy || !draft.trim()}>{busy === 'chat' ? '回应中…' : '发送 ↗'}</button></form></section>}
              <div className="result-end"><span>✓ 已自动保存在我的记录</span><button className="text-button" disabled={!!busy} onClick={() => { setReading(null); setRequestKey(null); setShowChat(false) }}>开始一次新的抽牌 →</button></div></>}
          </>}
      </>}
      {page === 'friends' && <><section className="page-heading"><span className="eyebrow">A LITTLE COMPANY</span><h1>总有一个角度，<br />让你愿意多说一点。</h1><p>几位不同性格的朋友，陪你探索同一个世界。</p></section><div className="friends-grid">{[['☾', '绯月', '直觉敏锐，偶尔有点俏皮。', '塔罗 · 从牌面聊到心事', true], ['☉', '星澈', '细致温柔，喜欢观察规律。', '星盘 · 正在准备', false], ['☷', '知微', '沉稳直接，也有生活的幽默。', '易经与灵签 · 正在准备', false]].map(([icon, name, desc, tag, ready]) => <section className="friend-card" key={String(name)}><span className="friend-icon">{icon}</span><h2>{name}</h2><p>{desc}</p><small>{tag}</small><button className="secondary" disabled={!ready || !!busy} onClick={() => { if (records.length) openRecord(records[0]); else { setReading(null); go('tarot') } }}>{ready ? '带一组牌来聊聊 ↗' : '即将见面'}</button></section>)}</div><p className="fine">当前开放塔罗结果内的绯月对话。独立私聊、自选群聊与长期记忆会在后续阶段加入。</p></>}
      {page === 'records' && <><section className="page-heading"><span className="eyebrow">YOUR LITTLE ARCHIVE</span><h1>那些留过回声的时刻。</h1><p>不必重新开始，可以接着上次的话题。</p></section><div className="section-heading"><h2>我的记录 <small>{records.length}</small></h2><button className="text-button" onClick={() => run('export', async () => { const data = await api('/api/export'); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = 'buxi-records.json'; a.click(); URL.revokeObjectURL(url) })} disabled={!!busy}>导出记录 ↓</button></div>
        {records.length === 0 ? <div className="empty-state"><Emblem small /><h2>故事还没开始。</h2><p>抽过的牌，会安静地留在这里。</p><button className="primary" onClick={() => { setReading(null); go('tarot') }}>开始第一次抽牌 ↗</button></div> : <div className="record-list">{records.map(r => <article key={r.id}><span className="record-icon">✦</span><button className="record-open" disabled={!!busy} onClick={() => openRecord(r)}><small>{new Date(r.created_at).toLocaleDateString()} · {r.spread === 'single' ? '单牌' : '三牌'}</small><h3>{r.question || '给此刻的自己'}</h3><p>{r.cards.map(c => c.name).join(' · ')}</p></button><button className="text-button delete" disabled={!!busy} onClick={() => { if (confirm('删除这次抽牌和关联聊天？此操作无法撤销。')) run('delete', async () => { await api('/api/results/' + r.id, undefined, 'DELETE'); refresh(); if (reading?.id === r.id) setReading(null) }) }}>删除</button></article>)}</div>}
        <p className="fine">数据存放在当前部署的 SQLite 数据库中。当前版本仅供本地个人使用。</p></>}
      <footer><span>卜犀 Buxi</span><span>A little insight. A little company.</span><small>娱乐与自我探索 · 不作为现实决策依据</small></footer>
    </main></div>
}
createRoot(document.getElementById('root')!).render(<App />);
