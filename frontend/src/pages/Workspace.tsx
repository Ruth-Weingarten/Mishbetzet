import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import Timetable, { Legend } from '../components/Timetable'
import { Book, Check, Pencil } from '../icons'
import type { Conflict, Proposal, Run, School } from '../types'

interface Props {
  school: School
  run: Run | null
  setRun: (r: Run) => void
}

export default function Workspace({ school, run, setRun }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function act(fn: () => Promise<Run>) {
    setBusy(true); setError(null)
    try { setRun(await fn()) } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const resume = (value: unknown) => act(() => api.resume(run!.id, value))

  if (!run) {
    return (
      <div className="page" style={{ maxWidth: 760 }}>
        <div className="card tape" style={{ padding: '34px 30px', textAlign: 'center' }}>
          <h1 className="chalk-title" style={{ fontSize: 64, margin: 0 }}>בניית המערכת</h1>
          <p style={{ fontSize: 17, lineHeight: 1.7 }}>
            המערכת תטען את הכיתות, המורות, טבלת השיבוץ, הכללים והטפסים,
            תתרגם את ההערות שכתבת, ותבקש ממך לאשר אותן לפני הבנייה.
          </p>
          {school.problems.length > 0 && (
            <div role="alert" style={{ textAlign: 'right', border: '2px solid #D9532C', background: '#FBE7DF', borderRadius: 6, padding: '12px 16px', margin: '0 0 18px', color: '#5E1F08' }}>
              <strong>לפני שבונים, צריך לתקן:</strong>
              <ul style={{ margin: '6px 0 0', paddingInlineStart: 20, lineHeight: 1.8 }}>
                {school.problems.map(p => <li key={p}>{p}</li>)}
              </ul>
            </div>
          )}
          <button className="btn pencil" disabled={busy} onClick={() => act(api.startRun)}>
            {busy ? 'טוען...' : 'התחלת בנייה'}
          </button>
          {error && <p style={{ color: '#8A2E0B' }}>{error}</p>}
        </div>
      </div>
    )
  }

  if (run.waiting?.type === 'review') {
    return <Review items={run.waiting.items} busy={busy} onApprove={ids => resume({ approved: ids })} />
  }

  return <Board school={school} run={run} busy={busy} error={error} resume={resume} />
}

/* ---------- עצירה 1: אישור התרגומים ---------- */

function Review({ items, busy, onApprove }: { items: Proposal[]; busy: boolean; onApprove: (ids: string[]) => void }) {
  const [on, setOn] = useState<Set<string>>(new Set(items.filter(i => i.matched).map(i => i.id)))
  const toggle = (id: string) => setOn(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  return (
    <div className="page" style={{ maxWidth: 900 }}>
      <div className="page-head">
        <div>
          <h1 className="chalk-title">כך הבנתי את ההערות</h1>
          <p>לפני שבונים: סמני את מה שהבנתי נכון. מה שלא סימנת לא ייכנס לבנייה.</p>
        </div>
        <button className="btn" disabled={busy} onClick={() => onApprove([...on])}>
          {busy ? 'בונה מערכת...' : `אישור ${on.size} כללים ובנייה`}
        </button>
      </div>
      <ul className="card" style={{ listStyle: 'none', margin: 0, padding: '6px 20px' }}>
        {items.map(p => (
          <li key={p.id} style={{ display: 'flex', gap: 14, alignItems: 'flex-start', padding: '14px 0', borderBottom: '1px solid var(--line)' }}>
            {p.matched ? (
              <button className="check" aria-pressed={on.has(p.id)} aria-label="סימון" onClick={() => toggle(p.id)}>
                {on.has(p.id) && <Check size={22} />}
              </button>
            ) : <span className="check" style={{ borderStyle: 'dashed', borderColor: '#9AA3A0' }} />}
            <div style={{ flex: 1 }}>
              <div className="muted" style={{ fontSize: 13 }}>{p.source} כתבה:</div>
              <div style={{ fontSize: 15, color: 'var(--l-ink)' }}>"{p.original}"</div>
              <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4 }}>
                {p.matched ? `← ${p.summary}` : '← לא נמצא כלל מתאים, והמערכת לא תנחש. אחרי הבנייה אפשר לכתוב לי עליה בצ\'אט במילים אחרות.'}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {busy && <Thinking text="פותר האילוצים בונה את המערכת. בבית ספר בגודל הזה זה יכול לקחת עד כמה דקות, אפשר להמשיך לחכות..." />}
    </div>
  )
}

/* ---------- סביבת העבודה: צ'אט + מערכת ---------- */

function Board({ school, run, busy, error, resume }: {
  school: School; run: Run; busy: boolean; error: string | null; resume: (v: unknown) => void
}) {
  const [mode, setMode] = useState<'class' | 'teacher'>('class')
  const [target, setTarget] = useState(school.classes[0])
  const [text, setText] = useState('')
  const bodyRef = useRef<HTMLDivElement>(null)
  const w = run.waiting

  // הודעה חדשה: גוללים לתחילתה, כדי שהתשובה תהיה מול העיניים ולא תיחבא מעל הפתקים.
  const seen = useRef(0)
  useEffect(() => {
    const body = bodyRef.current
    if (!body) return
    const first = body.children[seen.current] as HTMLElement | undefined
    if (seen.current > 0 && run.chat.length > seen.current && first) {
      body.scrollTo(0, Math.max(0, first.offsetTop - body.offsetTop - 8))
    } else {
      body.scrollTo(0, body.scrollHeight)
    }
    seen.current = run.chat.length
  }, [run.chat.length])
  useEffect(() => { if (busy) bodyRef.current?.scrollTo(0, bodyRef.current.scrollHeight) }, [busy])

  const flagged = useMemo(() => {
    const s = new Set<number>()
    for (const c of run.conflicts) for (const i of c.instances) {
      const [who, day] = i.key.split('|')
      if (who === target && day !== undefined) s.add(Number(day))
    }
    return s
  }, [run.conflicts, target])

  function send() {
    const t = text.trim()
    if (!t) return
    setText('')
    resume(w?.type === 'clarify' ? t : { kind: 'text', text: t })
  }

  const targets = mode === 'class' ? school.classes : school.teachers.map(t => t.name)

  return (
    <div className="page" style={{ display: 'flex', flexWrap: 'wrap', gap: 28, alignItems: 'flex-start' }}>
      <section className="card tape chat" aria-label="יומן ההתכתבות" style={{ flex: '1 1 380px', maxWidth: 470, minWidth: 0 }}>
        <div className="chat-head">
          <h2 className="chalk-title" style={{ margin: 0, fontSize: 34 }}>יומן ההתכתבות</h2>
          <p className="muted" style={{ margin: '4px 0 0', fontSize: 14 }}>
            סבב {run.round} · אפשר ללחוץ על אפשרות, או לכתוב במילים שלך
          </p>
        </div>

        <div className="chat-body" ref={bodyRef}>
          {run.chat.map((m, i) => m.role === 'principal'
            ? <div key={i} className="msg-me">{m.text}</div>
            : <div key={i} className="msg-sys"><Book /><span>{m.text}</span></div>)}

          {w?.type === 'decision' && run.conflicts.map((c, i) => (
            <ConflictCard key={c.id} c={c} n={i + 1} total={run.conflicts.length} busy={busy}
              onPick={o => resume({ kind: 'button', conflict_id: c.id, option: o })} />
          ))}

          {w?.type === 'clarify' && (
            <div className="sticky tilt-l"><strong>שאלת הבהרה:</strong> {w.question}</div>
          )}

          {w?.type === 'confirm' && (
            <div className="card" style={{ border: '2px solid var(--chalk)', padding: '14px 16px' }}>
              <strong>הבנתי כך:</strong>
              <div className="row" style={{ margin: '6px 0' }}><Check color="#2E4A3D" /> {w.summary}</div>
              <div style={{ fontSize: 14, lineHeight: 1.6, background: 'var(--paper)', padding: '6px 10px', borderRadius: 4 }}>
                <strong>מה ישתנה:</strong> {w.moved} שיעורים יזוזו.{' '}
                {w.added.length
                  ? <>במחיר: {w.added.map(a => `${a.text} (${a.count})`).join('; ')}.</>
                  : 'בלי לפגוע בשום כלל או בקשה.'}
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <button className="btn" disabled={busy} onClick={() => resume(true)}>אישור ובנייה מחדש</button>
                <button className="btn ghost" disabled={busy} onClick={() => resume(false)}>ביטול</button>
              </div>
            </div>
          )}

          {w?.type === 'decision' && !run.conflicts.length && !run.published && (
            <div className="sticky tilt-r">
              כל הכללים והבקשות מתקיימים. אפשר לאשר ולפרסם למורות.
            </div>
          )}

          {busy && <Thinking text="חושבת..." />}
          {error && <p style={{ color: '#8A2E0B' }}>{error}</p>}
        </div>

        <form className="chat-input" onSubmit={e => { e.preventDefault(); send() }}>
          <label htmlFor="msg" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>הודעה</label>
          <textarea id="msg" rows={2} value={text} disabled={busy || w?.type === 'confirm'}
            placeholder={w?.type === 'clarify' ? 'התשובה שלך...' : 'למשל: גולד ביום ראשון חופשי'}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
          <button className="send" type="submit" aria-label="שליחה" disabled={busy}><Pencil /></button>
        </form>
      </section>

      <section aria-label="מערכת השעות" style={{ flex: '999 1 560px', minWidth: 0 }}>
        <div className="page-head">
          <div>
            <h1 className="chalk-title">{mode === 'class' ? `כיתה ${target}` : `גב' ${target}`}</h1>
            <p>{mode === 'class' ? `מחנכת: ${school.homeroom[target]}` : `${school.teachers.find(t => t.name === target)?.hours ?? ''} שעות שבועיות`}</p>
          </div>
          <div className="row">
            <div className="pills" role="tablist">
              <button role="tab" aria-selected={mode === 'class'} className={`pill ${mode === 'class' ? 'on' : ''}`}
                onClick={() => { setMode('class'); setTarget(school.classes[0]) }}>לפי כיתה</button>
              <button role="tab" aria-selected={mode === 'teacher'} className={`pill ${mode === 'teacher' ? 'on' : ''}`}
                onClick={() => { setMode('teacher'); setTarget(school.teachers[0].name) }}>לפי מורה</button>
            </div>
            <label htmlFor="target" className="muted" style={{ fontSize: 14 }}>{mode === 'class' ? 'כיתה' : 'מורה'}</label>
            <select id="target" className="underline" value={target} onChange={e => setTarget(e.target.value)}>
              {targets.map(t => <option key={t}>{t}</option>)}
            </select>
            {w?.type === 'decision' && !run.published && (
              <button className="btn" disabled={busy} onClick={() => resume({ kind: 'approve' })}>אישור ופרסום למורות</button>
            )}
            {run.published && <span className="sticky" style={{ padding: '8px 12px' }}>פורסם למורות ✓</span>}
          </div>
        </div>
        <Timetable school={school} lessons={run.lessons} mode={mode} target={target} flaggedDays={flagged} />
        <Legend />
      </section>
    </div>
  )
}

function ConflictCard({ c, n, total, busy, onPick }: {
  c: Conflict; n: number; total: number; busy: boolean; onPick: (o: string) => void
}) {
  return (
    <div className={`sticky conflict ${n % 2 ? 'tilt-l' : 'tilt-r'}`}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3 className="chalk-title">{c.text}</h3>
        <span style={{ fontSize: 13, color: '#6B4E0A' }}>{n} מתוך {total}</span>
      </div>
      <p>{c.explanation}</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {c.options.map(o => (
          <button key={o.id} className="btn option" disabled={busy || o.disabled} onClick={() => onPick(o.id)}>
            {o.label}
            {o.impact && <span className="impact">{o.impact}</span>}
          </button>
        ))}
      </div>
    </div>
  )
}

function Thinking({ text }: { text: string }) {
  return <div className="thinking"><Pencil color="#2E4A3D" /> {text}</div>
}
