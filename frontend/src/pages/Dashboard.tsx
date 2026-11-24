import { Bell } from '../icons'
import type { Run, School } from '../types'

export default function Dashboard({ school, run, go }: { school: School; run: Run | null; go: (t: string) => void }) {
  const withForm = school.teachers.filter(t => t.form?.submitted)
  const stage = !run ? 5 : run.published ? 7 : 6
  const steps: [string, string][] = [
    ['מבנה', `${school.classes.length} כיתות · ${school.days.length} ימים`],
    ['מורות', `${school.teachers.length} מורות`],
    ['טפסים', `${withForm.length} מתוך ${school.teachers.length}`],
    ['שיבוץ', `${school.grades.length} שכבות`],
    ['כללים', `${school.rules.length} כללים · ${school.notes.length} הערות`],
    ['בנייה', run ? `סבב ${run.round}` : 'עוד לא התחיל'],
    ['פרסום', run?.published ? 'פורסם' : 'למורות'],
  ]
  const wednesday = withForm.filter(t => t.form?.free_day === 'רביעי').length

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="chalk-title" style={{ fontSize: 64 }}>הכנת המערכת לתשפ"ז</h1>
          <p>שלב אחר שלב. כל שלב נשמר, ואפשר לחזור אליו בכל זמן.</p>
        </div>
      </div>

      <div className="card" style={{ padding: '16px 20px', marginBottom: 30 }}>
        <h2 className="chalk-title" style={{ margin: '0 0 6px', fontSize: 34 }}>איך זה עובד</h2>
        <ol style={{ margin: 0, paddingInlineStart: 20, fontSize: 15, lineHeight: 1.9 }}>
          <li><strong>המורות ממלאות טופס</strong> (במתג "מורה" למעלה): יום חופשי, מקצועות, כיתה שאינן יכולות ללמד, ובקשות במילים שלהן.</li>
          <li><strong>את רואה את כל הטפסים</strong> בלשונית "טפסי מורות", כולל הסיבות שגלויות רק לך.</li>
          <li><strong>בלשוניות "שיבוץ" ו"כללים"</strong> מוגדר מי מלמדת מה, ומה הכללים של בית הספר.</li>
          <li><strong>ב"בניית המערכת"</strong> המערכת בונה בעצמה, מראה לך כל בקשה שלא הצליחה לקיים, ונותנת לך לבחור מה עדיף. אפשר גם לכתוב לה בצ'אט.</li>
          <li><strong>כשאת מרוצה</strong>, לוחצים "אישור ופרסום", וכל מורה רואה את המערכת שלה.</li>
        </ol>
      </div>

      <div style={{ paddingTop: 4, marginBottom: 34 }}>
        <div className="ruler" aria-hidden />
        <ol className="steps" aria-label="שלבי ההכנה">
          {steps.map(([name, info], i) => {
            const st = i + 1 < stage ? 'done' : i + 1 === stage ? 'now' : 'todo'
            return (
              <li key={name}>
                <span className={`dot ${st}`}>{st === 'done' ? '✓' : i + 1}</span>
                <span style={{ fontSize: 17, fontWeight: 800, marginTop: 8 }}>{name}</span>
                <span className="muted" style={{ fontSize: 14 }}>{info}</span>
              </li>
            )
          })}
        </ol>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 28, alignItems: 'flex-start' }}>
        <section className="card" style={{ flex: '1 1 440px', minWidth: 0, padding: '22px 22px 16px', cursor: 'pointer' }} onClick={() => go('forms')}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div>
              <h2 className="chalk-title" style={{ margin: 0, fontSize: 38 }}>טפסי המורות</h2>
              <p className="muted" style={{ margin: '2px 0 0' }}>{withForm.length} מתוך {school.teachers.length} מילאו</p>
            </div>
            <button className="btn ghost row" style={{ gap: 8 }}><Bell size={18} /> צלצול תזכורת ל־{school.teachers.length - withForm.length}</button>
          </div>
          <ul className="lined" style={{ listStyle: 'none', margin: '10px 0 0', padding: 0 }}>
            {withForm.map(t => (
              <li key={t.name} className="row" style={{ justifyContent: 'space-between', height: 48, fontSize: 15 }}>
                <strong>גב' {t.name}</strong>
                <span className="muted" style={{ fontSize: 14 }}>
                  {t.form?.free_day} חופשי{t.form?.alt_day ? `, או ${t.form.alt_day}` : ''}
                  {t.form?.free_text ? ' · בקשה נוספת' : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section style={{ flex: '1 1 340px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 26 }}>
          <div style={{ background: 'var(--chalk)', border: '10px solid var(--wood)', borderRadius: 4, color: '#F4F1E8', padding: '18px 22px 20px' }}>
            <h2 className="chalk-title" style={{ margin: 0, fontSize: 40 }}>הצעד הבא</h2>
            <p style={{ fontSize: 16, lineHeight: 1.6 }}>
              {!run ? 'כל הנתונים מוכנים. אפשר להתחיל לבנות את המערכת.'
                : run.published ? 'המערכת פורסמה. תיקונים אפשר לבקש בצ\'אט.'
                : 'יש החלטות שמחכות לך בסביבת העבודה.'}
            </p>
            <button className="btn pencil" onClick={() => go('work')}>לבניית המערכת</button>
          </div>
          <div className="sticky tilt-r">
            <h3 className="chalk-title" style={{ margin: '0 0 6px', fontSize: 32 }}>לשים לב</h3>
            <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 15, lineHeight: 1.8 }}>
              <li>{wednesday} מורות ביקשו את יום רביעי כיום חופשי</li>
              <li>{school.teachers.filter(t => t.blocked.length).length} מורות סימנו כיתה שאינן יכולות ללמד</li>
              <li>{school.notes.length} הערות חופשיות יתורגמו לכללים</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  )
}
