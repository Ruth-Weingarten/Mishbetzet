import type { Lesson, School } from '../types'

interface Props {
  school: School
  lessons: Lesson[]
  mode: 'class' | 'teacher'
  target: string
  flaggedDays?: Set<number>
}

export default function Timetable({ school, lessons, mode, target, flaggedDays }: Props) {
  const maxP = Math.max(...school.periodsPerDay)
  const mine = lessons.filter(l => (mode === 'class' ? l.cls === target : l.teachers.includes(target)))
  const at = (d: number, p: number) => mine.filter(l => l.day === d && l.period === p)

  return (
    <div className="card grid-paper">
      <div className="tt">
        <div className="tt-row">
          <div />
          {school.days.map((d, i) => (
            <div key={d} className="tt-day chalk-title">
              {d}
              {flaggedDays?.has(i) && <span className="flag">יש כאן חריגה</span>}
            </div>
          ))}
        </div>
        {Array.from({ length: maxP }, (_, p) => (
          <div key={p} className="tt-row">
            <div className="tt-num">
              <div>
                <span>{p + 1}</span>
                <small>{school.periodTimes[p][0]}</small>
              </div>
            </div>
            {school.days.map((_, d) => {
              if (p >= school.periodsPerDay[d]) return <div key={d} />
              const here = at(d, p)
              if (!here.length) return <div key={d} className="lesson empty" />
              // השיעור הראשי של המשבצת (שיעור סיוע מוצג כתוספת)
              const l = here.find(x => !x.pullout) ?? here[0]
              const extra = here.filter(x => x.pullout && x !== l)
              // בתצוגת מורה: הקבצה = אותו מקצוע בכמה כיתות באותה שעה
              const classes = [...new Set(here.filter(x => x.subject === l.subject).map(x => x.cls))]
              const hl = flaggedDays?.has(d) && p === 0
              return (
                <div key={d} className={`lesson g-${l.group}${hl ? ' hl' : ''}`}>
                  <b>{mode === 'class' ? l.subject : `${classes.join(', ')} · ${l.subject}`}</b>
                  <span>
                    {mode === 'class'
                      ? (l.teachers.length > 3 ? `${l.teachers.length} מורות (הקבצה)` : l.teachers.join(' + '))
                      : l.teachers.length > 1 ? 'מקביל' : ''}
                    {l.room ? ` · ${l.room}` : ''}
                  </span>
                  {extra.map(x => <span key={x.subject}>+ {x.subject}{mode === 'class' ? ` (${x.teachers.join(', ')})` : ''}</span>)}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

export function Legend() {
  const items: [string, string][] = [
    ['kodesh', 'קודש'], ['lang', 'שפה'], ['math', 'חשבון'], ['science', 'מדעים ומולדת'], ['other', 'אחר'],
  ]
  return (
    <div className="row muted" style={{ fontSize: 13, gap: 16, marginTop: 10 }}>
      {items.map(([g, t]) => (
        <span key={g} className="row" style={{ gap: 6 }}>
          <span aria-hidden className={`g-${g}`} style={{ width: 22, height: 6, borderRadius: 3, borderBottomWidth: 6, borderBottomStyle: 'solid' }} />
          {t}
        </span>
      ))}
    </div>
  )
}
