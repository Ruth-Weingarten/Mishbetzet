import { useState } from 'react'
import { Check, Pencil } from '../icons'
import { api } from '../api'
import type { Rule, School } from '../types'

// שמות בעברית למספרים שאפשר לערוך בכלל
const PARAM_LABELS: Record<string, string> = {
  min_days: 'מינימום ימים',
  max: 'מקסימום',
  max_per_day: 'מקסימום ביום',
  min: 'מינימום שיעורים ביום',
  max_lessons: 'מקסימום שיעורים',
  last_period: 'שעה אחרונה (0 = ראשונה)',
  threshold: 'סף שעות',
  above: 'ימי עבודה מעל הסף',
  below: 'ימי עבודה עד הסף',
  tolerance: 'סטייה מותרת',
  max_wait: 'מקסימום שעות המתנה',
  min_free_days: 'ימים חופשיים',
}

function numericParams(r: Rule): [string, number][] {
  return Object.entries(r.params).filter(([, v]) => typeof v === 'number') as [string, number][]
}

export default function Rules({ school, onChanged }: { school: School; onChanged: () => void }) {
  const [editing, setEditing] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [nums, setNums] = useState<Record<string, number>>({})
  const [error, setError] = useState('')

  const act = async (fn: () => Promise<unknown>) => {
    setError('')
    try { await fn(); onChanged() } catch (e) { setError((e as Error).message) }
  }

  const open = (r: Rule) => {
    setEditing(r.id)
    setText(r.text)
    setNums(Object.fromEntries(numericParams(r)))
  }

  const save = (r: Rule) => act(async () => {
    await api.patchRule(r.id, { text, params: nums })
    setEditing(null)
  })

  const off = school.rules.filter(r => r.enabled === false).length

  return (
    <div className="page" style={{ display: 'flex', flexWrap: 'wrap', gap: 32, alignItems: 'flex-start' }}>
      <section style={{ flex: '999 1 560px', minWidth: 0 }}>
        <div className="page-head">
          <div>
            <h1 className="chalk-title" style={{ fontSize: 62 }}>כללי בית הספר</h1>
            <p>נשמרו מתשפ"ו. המערכת תנסה לקיים את כולם, וכשאי אפשר, תשאל אותך.</p>
            <p className="muted" style={{ fontSize: 14 }}>
              אפשר לבטל כלל (הסימון משמאל) או לערוך אותו. השינוי חל מהבנייה הבאה
              {off ? `. כרגע ${off} כללים מבוטלים.` : '.'}
            </p>
          </div>
        </div>
        {error && <p role="alert" style={{ color: '#B3261E' }}>{error}</p>}
        <ul className="card" style={{ listStyle: 'none', margin: 0, padding: '6px 20px' }}>
          {school.rules.map(r => {
            const on = r.enabled !== false
            return (
              <li key={r.id} style={{ borderBottom: '1px solid var(--line)', padding: '10px 0' }}>
                <div className="row" style={{ minHeight: 44, gap: 14, flexWrap: 'nowrap' }}>
                  <button className="check" aria-pressed={on} aria-label={on ? 'ביטול הכלל' : 'הפעלת הכלל'}
                    title={on ? 'לחצי כדי לבטל את הכלל' : 'הכלל מבוטל. לחצי כדי להפעיל'}
                    onClick={() => act(() => api.patchRule(r.id, { enabled: !on }))}>
                    {on && <Check size={22} />}
                  </button>
                  <span style={{ flex: 1, fontSize: 16, fontWeight: 700, opacity: on ? 1 : 0.5,
                    textDecoration: on ? 'none' : 'line-through' }}>{r.text}</span>
                  <button className="send" aria-label="עריכת הכלל" onClick={() => (editing === r.id ? setEditing(null) : open(r))}
                    style={{ background: 'transparent', boxShadow: 'none', color: 'var(--chalk)' }}><Pencil size={20} /></button>
                </div>
                {editing === r.id && (
                  <div style={{ padding: '8px 0 6px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 14 }}>
                      ניסוח הכלל
                      <input value={text} onChange={e => setText(e.target.value)} style={{ fontSize: 15, padding: 6 }} />
                    </label>
                    {numericParams(r).length > 0 && (
                      <div className="row" style={{ gap: 14 }}>
                        {numericParams(r).map(([k]) => (
                          <label key={k} style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 14 }}>
                            {PARAM_LABELS[k] ?? k}
                            <input type="number" value={nums[k] ?? 0} style={{ width: 120, fontSize: 15, padding: 6 }}
                              onChange={e => setNums({ ...nums, [k]: Number(e.target.value) })} />
                          </label>
                        ))}
                      </div>
                    )}
                    <div className="row">
                      <button className="btn" onClick={() => save(r)}>שמירה</button>
                      <button className="btn ghost" onClick={() => setEditing(null)}>ביטול</button>
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </section>

      <section style={{ flex: '1 1 360px', maxWidth: 460, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 22 }}>
        <div>
          <h2 className="chalk-title" style={{ margin: 0, fontSize: 44 }}>הערות במילים שלך</h2>
          <p className="muted" style={{ margin: '2px 0 0', fontSize: 14 }}>
            לכל מה שלא ברשימה. בתחילת הבנייה המערכת מתרגמת אותן לכללים, ומבקשת ממך לאשר.
          </p>
        </div>
        {school.notes.map((n, i) => (
          <div key={n.id} className={`sticky ${i % 2 ? 'tilt-r' : 'tilt-l'}`} style={{ fontSize: 15, lineHeight: 1.7 }}>
            "{n.text}"
          </div>
        ))}
      </section>
    </div>
  )
}
