import { useState } from 'react'
import { api } from '../api'
import type { School } from '../types'

const TAB_COLORS = ['#F2C14E', '#A9CBE3', '#E9B8A6', '#B7D3B0']

export default function Assignment({ school, onChanged }: { school: School; onChanged: () => void }) {
  const [grade, setGrade] = useState(school.grades[0])
  const [edit, setEdit] = useState<{ cls: string; subject: string; teachers: string[] } | null>(null)
  const [error, setError] = useState('')
  const names = school.teachers.map(t => t.name).sort((a, b) => a.localeCompare(b, 'he'))

  const save = async () => {
    if (!edit) return
    setError('')
    try {
      await api.patchAssignment(edit.cls, edit.subject, edit.teachers)
      setEdit(null)
      onChanged()
    } catch (e) { setError((e as Error).message) }
  }
  const classes = school.classes.filter(c => c.startsWith(grade))
  const cell = (c: string, s: string) => school.assignment.find(a => a.cls === c && a.subject === s)
  // המקצועות של השכבה: כל מקצוע שנלמד לפחות באחת הכיתות שלה
  const subjects = Object.keys(school.curriculum).filter(s => classes.some(c => s in school.classCurriculum[c]))

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="chalk-title">שיבוץ מורות · שכבה {grade}</h1>
          <p>מי מלמדת כל מקצוע בכל כיתה, וכמה שעות. לחצי על משבצת כדי להחליף מורה. השינוי חל מהבנייה הבאה, ונשמר עד שהשרת מופעל מחדש.</p>
        </div>
      </div>
      {school.problems.length > 0 && (
        <div role="alert" className="card" style={{ border: '2px solid #D9532C', background: '#FBE7DF', padding: '14px 18px', marginBottom: 22 }}>
          <strong style={{ color: '#5E1F08' }}>עם הנתונים האלה אי אפשר לבנות מערכת:</strong>
          <ul style={{ margin: '6px 0 0', paddingInlineStart: 20, lineHeight: 1.8, color: '#5E1F08' }}>
            {school.problems.map(p => <li key={p}>{p}</li>)}
          </ul>
        </div>
      )}

      <div role="tablist" className="row" style={{ gap: 4, paddingInlineStart: 10 }}>
        {school.grades.map((g, i) => (
          <button key={g} role="tab" aria-selected={g === grade} className={`tab ${g === grade ? 'active' : ''}`}
            style={{ background: TAB_COLORS[i % 4], opacity: g === grade ? 1 : 0.8 }} onClick={() => setGrade(g)}>
            שכבה {g}
          </button>
        ))}
      </div>
      <div className="card grid-paper" style={{ borderTop: '4px solid #A9CBE3', borderRadius: '0 0 4px 4px' }}>
        <table className="sheet">
          <thead>
            <tr>
              <th className="chalk-title" style={{ fontSize: 26, textAlign: 'right', width: 160 }}>מקצוע</th>
              {classes.map(c => (
                <th key={c}>
                  <div className="chalk-title" style={{ fontSize: 30, color: 'var(--chalk)' }}>{c}</div>
                  <div className="muted" style={{ fontSize: 12 }}>מחנכת: {school.homeroom[c]}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {subjects.map(s => {
              const g = school.subjects[s]
              const first = cell(classes[0], s)
              const allPool = classes.every(c => cell(c, s)?.kind === 'pool')
              const hours = new Set(classes.map(c => school.classCurriculum[c][s]).filter(Boolean))
              return (
                <tr key={s}>
                  <th scope="row" className={`subj g-${g}`}>{s} {hours.size === 1 && <span style={{ fontWeight: 600, opacity: 0.8 }}>· {[...hours][0]}</span>}</th>
                  {allPool ? (
                    <td colSpan={classes.length}>
                      <div className="pool">
                        <span><strong>מאגר:</strong> {first?.teachers.join(', ')} · לכל {classes.length} הכיתות</span>
                        <span style={{ fontSize: 13 }}>המערכת תבחר · עדיף לא בכיתה שחינכה בשנה שעברה</span>
                      </div>
                    </td>
                  ) : classes.map(c => {
                    const a = cell(c, s)
                    if (!a) return <td key={c}><div className="cell muted">—</div></td>
                    const h = school.classCurriculum[c][s]
                    const clash = a.kind !== 'pool' && a.teachers.some(t => school.teachers.find(x => x.name === t)?.blocked.includes(c))
                    return (
                      <td key={c}>
                        <div className={`cell ${a.homeroom ? 'hr' : ''}`} role="button" tabIndex={0}
                          onClick={() => setEdit({ cls: c, subject: s, teachers: [...a.teachers] })}
                          onKeyDown={e => { if (e.key === 'Enter') setEdit({ cls: c, subject: s, teachers: [...a.teachers] }) }}
                          style={{ cursor: 'pointer', ...(clash ? { background: '#FBE7DF', border: '2px solid #D9532C' } : {}) }}>
                          {a.homeroom ? 'מחנכת' : a.block ? 'הקבצה' : a.teachers[0]}
                          {a.block && <span style={{ display: 'block', fontSize: 12 }} className="muted">{a.teachers.length} מורות, יחד עם כיתות מקבילות</span>}
                          {!a.block && a.kind === 'parallel' && <span style={{ display: 'block', fontSize: 12 }} className="muted">+ {a.teachers.slice(1).join(', ')} (מקביל)</span>}
                          {a.pullout && <span style={{ display: 'block', fontSize: 12 }} className="muted">במקביל לשיעור אחר</span>}
                          {hours.size > 1 && <span style={{ display: 'block', fontSize: 12 }} className="muted">{h} ש'</span>}
                          {clash && <span style={{ display: 'block', fontSize: 12, fontWeight: 800, color: '#8A2E0B' }}>ביקשה לא ללמד כיתה זו</span>}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {edit && (
        <div className="card" role="dialog" aria-label="עריכת שיבוץ" style={{ marginTop: 18, padding: '16px 20px', border: '2px solid var(--chalk)' }}>
          <h2 style={{ margin: '0 0 6px', fontSize: 22 }}>{edit.subject} · {edit.cls}</h2>
          {(school.assignment.find(a => a.cls === edit.cls && a.subject === edit.subject)?.block) && (
            <p className="muted" style={{ margin: '0 0 8px', fontSize: 14 }}>זו הקבצה: השינוי חל על כל הכיתות שבה.</p>
          )}
          {(school.assignment.find(a => a.cls === edit.cls && a.subject === edit.subject)?.homeroom) && (
            <p className="muted" style={{ margin: '0 0 8px', fontSize: 14 }}>זו משבצת של המחנכת: החלפה תחליף את מחנכת הכיתה בכל המקצועות שלה.</p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 420 }}>
            {edit.teachers.map((t, i) => (
              <div key={i} className="row" style={{ flexWrap: 'nowrap' }}>
                <select value={t} style={{ flex: 1, fontSize: 15, padding: 6 }} aria-label={`מורה ${i + 1}`}
                  onChange={e => setEdit({ ...edit, teachers: edit.teachers.map((x, j) => (j === i ? e.target.value : x)) })}>
                  {names.map(n => <option key={n} value={n}>{n}</option>)}
                </select>
                {edit.teachers.length > 1 && (
                  <button className="btn ghost" onClick={() => setEdit({ ...edit, teachers: edit.teachers.filter((_, j) => j !== i) })}>הסרה</button>
                )}
              </div>
            ))}
          </div>
          {error && <p role="alert" style={{ color: '#B3261E' }}>{error}</p>}
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn" onClick={save}>שמירה</button>
            <button className="btn ghost" onClick={() => setEdit({ ...edit, teachers: [...edit.teachers, names[0]] })}>הוספת מורה במקביל</button>
            <button className="btn ghost" onClick={() => { setEdit(null); setError('') }}>ביטול</button>
          </div>
        </div>
      )}
    </div>
  )
}
