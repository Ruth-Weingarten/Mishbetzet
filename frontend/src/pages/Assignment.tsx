import { useState } from 'react'
import type { School } from '../types'

const TAB_COLORS = ['#F2C14E', '#A9CBE3', '#E9B8A6', '#B7D3B0']

export default function Assignment({ school }: { school: School }) {
  const [grade, setGrade] = useState(school.grades[0])
  const classes = school.classes.filter(c => c.startsWith(grade))
  const cell = (c: string, s: string) => school.assignment.find(a => a.cls === c && a.subject === s)
  // המקצועות של השכבה: כל מקצוע שנלמד לפחות באחת הכיתות שלה
  const subjects = Object.keys(school.curriculum).filter(s => classes.some(c => s in school.classCurriculum[c]))

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="chalk-title">שיבוץ מורות · שכבה {grade}</h1>
          <p>מי מלמדת כל מקצוע בכל כיתה, וכמה שעות. בהדגמה הטבלה קבועה, ובגרסה המלאה היא נפתחת מהשנה הקודמת וניתנת לעריכה.</p>
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
                        <div className={`cell ${a.homeroom ? 'hr' : ''}`} style={clash ? { background: '#FBE7DF', border: '2px solid #D9532C' } : undefined}>
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
    </div>
  )
}
