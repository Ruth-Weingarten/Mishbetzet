import { useEffect, useState } from 'react'
import { api } from '../api'
import { Bell } from '../icons'
import type { Form, School } from '../types'

type Row = { teacher: string; hours: number; form: Form | null }

export default function Forms({ school }: { school: School }) {
  const [rows, setRows] = useState<Row[]>([])
  const [day, setDay] = useState<string | null>(null)
  const [onlyMissing, setOnlyMissing] = useState(false)

  useEffect(() => { api.forms().then(setRows) }, [])

  const filled = rows.filter(r => r.form?.submitted)
  const shown = rows.filter(r =>
    onlyMissing ? !r.form?.submitted : (!day || r.form?.free_day === day))
  const byDay = (d: string) => filled.filter(r => r.form?.free_day === d).length

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="chalk-title">טפסי המורות</h1>
          <p>{filled.length} מתוך {rows.length} מילאו. הסיבות והבקשות האישיות גלויות לך בלבד.</p>
        </div>
        <button className="btn ghost row" style={{ gap: 8 }}><Bell size={18} /> צלצול תזכורת ל־{rows.length - filled.length} שעוד לא מילאו</button>
      </div>

      <div className="card" style={{ padding: '14px 18px', marginBottom: 22 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>כמה מורות ביקשו כל יום חופשי</div>
        <div className="pills">
          <button className={`pill ${!day && !onlyMissing ? 'on' : ''}`} onClick={() => { setDay(null); setOnlyMissing(false) }}>כולן</button>
          {school.days.map(d => (
            <button key={d} className={`pill ${day === d && !onlyMissing ? 'on' : ''}`} onClick={() => { setDay(d); setOnlyMissing(false) }}>
              {d} · {byDay(d)}
            </button>
          ))}
          <button className={`pill ${onlyMissing ? 'on' : ''}`} onClick={() => setOnlyMissing(true)}>לא מילאו</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 22 }}>
        {shown.map((r, i) => {
          const f = r.form
          return (
            <article key={r.teacher} className={`card ${i % 3 === 1 ? 'tilt-r' : ''}`} style={{ padding: '16px 18px', opacity: f?.submitted ? 1 : 0.7 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <h2 className="chalk-title" style={{ margin: 0, fontSize: 34 }}>גב' {r.teacher}</h2>
                <span className="muted" style={{ fontSize: 13 }}>{r.hours} ש' בשיבוץ</span>
              </div>
              {!f?.submitted ? (
                <p className="muted">עוד לא מילאה את הטופס</p>
              ) : (
                <dl className="lined" style={{ margin: '8px 0 0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '0 12px', fontSize: 14, lineHeight: '30px' }}>
                  <dt className="muted">יום חופשי</dt>
                  <dd style={{ margin: 0, fontWeight: 700 }}>{f.free_day ?? 'לא ביקשה'}{f.alt_day ? `, או ${f.alt_day}` : ''}</dd>
                  <dt className="muted">מקצועות</dt>
                  <dd style={{ margin: 0 }}>{f.subjects.length ? f.subjects.join(', ') : '—'}</dd>
                  {f.blocked_class && <>
                    <dt className="muted">לא ללמד</dt>
                    <dd style={{ margin: 0, fontWeight: 800, color: '#8A2E0B' }}>{f.blocked_class}{f.reason ? ` · 🔒 ${f.reason}` : ''}</dd>
                  </>}
                  {f.leave && <>
                    <dt className="muted">חופשה</dt>
                    <dd style={{ margin: 0 }}>כן{f.leave_when ? `, ${f.leave_when}` : ''}</dd>
                  </>}
                  {f.reduce_hours > 0 && <>
                    <dt className="muted">הורדת שעות</dt>
                    <dd style={{ margin: 0 }}>{f.reduce_hours}</dd>
                  </>}
                </dl>
              )}
              {f?.free_text && (
                <div className="sticky" style={{ marginTop: 14, padding: '12px 12px 10px', fontSize: 14, lineHeight: 1.6 }}>
                  <div style={{ color: 'var(--l-ink)' }}>"{f.free_text}"</div>
                  <div style={{ fontWeight: 700, marginTop: 4 }}>
                    {f.confirmed_rule
                      ? `← המורה אישרה: ${f.confirmed_rule.summary}`
                      : '← יתורגם בתחילת הבנייה, ותאשרי אותו'}
                  </div>
                </div>
              )}
            </article>
          )
        })}
      </div>
    </div>
  )
}
