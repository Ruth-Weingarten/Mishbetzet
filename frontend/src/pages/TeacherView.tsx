import { useEffect, useState } from 'react'
import { api } from '../api'
import Timetable, { Legend } from '../components/Timetable'
import type { Form, Run, School } from '../types'

const EMPTY: Form = {
  free_day: null, alt_day: null, subjects: [], blocked_class: null, reason: '',
  leave: false, leave_when: '', reduce_hours: 0, free_text: '',
}

const lineStyle = {
  width: '100%', fontSize: 15, lineHeight: '28px', border: 0, background: 'transparent', color: 'var(--l-ink)',
  resize: 'none' as const,
  backgroundImage: 'repeating-linear-gradient(to bottom, transparent 0, transparent 27px, var(--line) 27px, var(--line) 28px)',
}

export default function TeacherView({ school, run, me, onSaved }: { school: School; run: Run | null; me: string; onSaved: () => void }) {
  const [form, setForm] = useState<Form>(EMPTY)
  const [savedText, setSavedText] = useState('')
  const [pending, setPending] = useState<{ thread: string; summary: string; matched: boolean } | null>(null)
  const [confirmedText, setConfirmedText] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setPending(null); setMsg(null)
    api.myForm(me).then(f => {
      setForm({ ...EMPTY, ...f })
      setSavedText(f.free_text)
      setConfirmedText(f.confirmed_rule ? f.free_text : null)
    })
  }, [me])

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm(f => ({ ...f, [k]: v }))
  const toggleSubject = (s: string) =>
    set('subjects', form.subjects.includes(s) ? form.subjects.filter(x => x !== s) : [...form.subjects, s])

  const textNeedsCheck = form.free_text.trim() !== '' && confirmedText !== form.free_text

  async function save() {
    // תרגום שהמורה אישרה כבר נשמר בשרת, ונשאר מחובר לטופס כל עוד הטקסט לא השתנה
    await api.saveForm(me, form)
    setSavedText(form.free_text)
    setMsg('הטופס נשלח למנהלת. אפשר לחזור ולעדכן עד שהמערכת נבנית.')
    onSaved()
  }

  async function submit() {
    setBusy(true); setMsg(null)
    if (textNeedsCheck) {
      // יש טקסט חופשי חדש: מראים למורה איך הובן, לפני השליחה
      const r = await api.teacherTranslate(me, form.free_text)
      setPending({ thread: r.thread, summary: r.proposal.summary, matched: r.proposal.matched })
    } else {
      await save()
    }
    setBusy(false)
  }

  async function answer(ok: boolean) {
    setBusy(true)
    await api.teacherConfirm(pending!.thread, ok)
    const matched = pending!.matched
    setPending(null)
    if (ok && matched) setConfirmedText(form.free_text)
    if (ok) await save()
    setBusy(false)
  }

  const dayBtn = (d: string, on: boolean, onClick: () => void) => (
    <button key={d} type="button" aria-pressed={on} className={`pill ${on ? 'on' : ''}`}
      style={{ borderColor: 'var(--chalk)', ...(on ? { background: 'var(--chalk)' } : { color: 'var(--chalk)' }) }}
      onClick={onClick}>{d}</button>
  )

  return (
    <div className="page" style={{ display: 'flex', flexWrap: 'wrap', gap: 32, alignItems: 'flex-start' }}>
      <section className="card tape" style={{ flex: '1 1 360px', maxWidth: 460, padding: '22px 22px 20px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div>
          <h1 className="chalk-title" style={{ margin: 0, fontSize: 44 }}>הערכות לשנה הבאה</h1>
          <p className="muted" style={{ margin: '2px 0 0' }}>הטופס של גב' {me}</p>
        </div>

        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend style={{ fontWeight: 800, marginBottom: 4 }}>יום חופשי רצוי</legend>
          <p className="muted" style={{ margin: '0 0 8px', fontSize: 13 }}>בהשתדלות, ללא התחייבות</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0,1fr))', gap: 8 }}>
            {school.days.map(d => dayBtn(d, form.free_day === d, () => set('free_day', form.free_day === d ? null : d)))}
          </div>
          <p style={{ margin: '12px 0 6px', fontSize: 14 }}>ואם אי אפשר, יום חלופי:</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0,1fr))', gap: 8 }}>
            {school.days.filter(d => d !== form.free_day).map(d =>
              dayBtn(d, form.alt_day === d, () => set('alt_day', form.alt_day === d ? null : d)))}
          </div>
        </fieldset>

        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend style={{ fontWeight: 800, marginBottom: 8 }}>מקצועות שהייתי שמחה ללמד</legend>
          <div className="pills">
            {Object.keys(school.curriculum).filter(s => !s.includes('/') && !s.includes('(')).map(s => (
              <button key={s} type="button" aria-pressed={form.subjects.includes(s)}
                className={`pill g-${school.subjects[s]}`}
                style={{ borderWidth: 2, borderStyle: form.subjects.includes(s) ? 'solid' : 'dashed', opacity: form.subjects.includes(s) ? 1 : 0.65, fontWeight: form.subjects.includes(s) ? 800 : 600 }}
                onClick={() => toggleSubject(s)}>{s}</button>
            ))}
          </div>
        </fieldset>

        <div>
          <label htmlFor="blocked" style={{ display: 'block', fontWeight: 800 }}>כיתה שאינני יכולה ללמד</label>
          <select id="blocked" className="underline" style={{ width: '100%' }} value={form.blocked_class ?? ''}
            onChange={e => set('blocked_class', e.target.value || null)}>
            <option value="">אין</option>
            {school.classes.map(c => <option key={c}>{c}</option>)}
          </select>
          {form.blocked_class && (
            <>
              <label htmlFor="reason" style={{ display: 'block', fontSize: 14, marginTop: 10 }}>פרטי את הסיבה</label>
              <textarea id="reason" rows={1} value={form.reason} onChange={e => set('reason', e.target.value)} style={lineStyle} />
              <p className="muted" style={{ margin: '4px 0 0', fontSize: 13 }}>🔒 הסיבה גלויה למנהלת בלבד</p>
            </>
          )}
        </div>

        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend style={{ fontWeight: 800, marginBottom: 8 }}>האם את יוצאת לחופשה השנה?</legend>
          <div className="row">
            {[false, true].map(v => (
              <button key={String(v)} type="button" className={`pill ${form.leave === v ? 'on' : ''}`} onClick={() => set('leave', v)}>{v ? 'כן' : 'לא'}</button>
            ))}
            {form.leave && (
              <label className="row" style={{ gap: 6, fontSize: 14 }}>זמן משוער:
                <input value={form.leave_when} onChange={e => set('leave_when', e.target.value)}
                  style={{ border: 0, borderBottom: '2px solid var(--chalk)', background: 'transparent', fontSize: 15, width: 120 }} />
              </label>
            )}
          </div>
        </fieldset>

        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend style={{ fontWeight: 800, marginBottom: 8 }}>האם את מעוניינת להוריד שעות?</legend>
          <div className="row">
            {[false, true].map(v => (
              <button key={String(v)} type="button" className={`pill ${(form.reduce_hours > 0) === v ? 'on' : ''}`}
                onClick={() => set('reduce_hours', v ? Math.max(form.reduce_hours, 1) : 0)}>{v ? 'כן' : 'לא'}</button>
            ))}
            {form.reduce_hours > 0 && (
              <label className="row" style={{ gap: 6, fontSize: 14 }}>כמה שעות:
                <input type="number" min={1} max={20} value={form.reduce_hours} onChange={e => set('reduce_hours', Number(e.target.value))}
                  style={{ border: 0, borderBottom: '2px solid var(--chalk)', background: 'transparent', fontSize: 15, width: 60 }} />
              </label>
            )}
          </div>
        </fieldset>

        <div>
          <label htmlFor="free" style={{ display: 'block', fontWeight: 800 }}>הערות ובקשות ביחס למערכת הכיתתית או האישית</label>
          <textarea id="free" rows={3} value={form.free_text} onChange={e => set('free_text', e.target.value)}
            placeholder="למשל: ביום חמישי לא לפני 9" style={lineStyle} />
          {!textNeedsCheck && form.free_text && <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--chalk)', fontWeight: 700 }}>✓ אישרת איך המערכת הבינה את הבקשה</p>}
        </div>

        {pending ? (
          <div className="sticky tilt-l" role="status">
            <strong>{pending.matched ? 'רגע לפני השליחה: כך הבנו את הבקשה' : 'לא הצלחנו לתרגם את הבקשה לכלל'}</strong>
            <p style={{ margin: '6px 0 10px' }}>
              {pending.matched ? pending.summary : 'אפשר לשלוח אותה כך, והמנהלת תראה אותה כהערה. או לנסח אחרת.'}
            </p>
            <div className="row">
              <button className="btn" disabled={busy} onClick={() => answer(true)}>{pending.matched ? 'נכון, לשלוח' : 'לשלוח כך'}</button>
              <button className="btn ghost" disabled={busy} onClick={() => answer(false)}>לתקן</button>
            </div>
          </div>
        ) : (
          <>
            {msg && <p style={{ margin: 0, fontWeight: 700, color: 'var(--chalk)' }}>{msg}</p>}
            <button className="btn pencil" disabled={busy} onClick={submit}>
              {busy ? 'רגע...' : savedText === form.free_text && msg ? 'עדכון הטופס' : 'שליחת הטופס'}
            </button>
          </>
        )}
      </section>

      <section style={{ flex: '999 1 560px', minWidth: 0 }}>
        <div className="page-head">
          <div>
            <h1 className="chalk-title">המערכת שלי</h1>
            <p>{run?.published ? 'המערכת שפורסמה על ידי המנהלת' : 'המערכת תוצג כאן אחרי שהמנהלת תאשר ותפרסם אותה.'}</p>
          </div>
        </div>
        {run?.published && (
          <>
            <Timetable school={school} lessons={run.lessons} mode="teacher" target={me} />
            <Legend />
          </>
        )}
      </section>
    </div>
  )
}
