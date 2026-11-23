import { Bell, Book, Check, Pencil } from '../icons'

export default function Home({ onLogin }: { onLogin: () => void }) {
  return (
    <div>
      {/* ----- כותרת ראשית על הלוח ----- */}
      <section style={{
        background: 'var(--chalk)', color: '#F4F1E8', borderBottom: '14px solid var(--wood)',
        backgroundImage: 'radial-gradient(ellipse at 70% 30%, rgba(255,255,255,0.08), transparent 60%)',
        padding: '70px 28px 80px',
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', flexWrap: 'wrap', gap: 50, alignItems: 'center' }}>
          <div style={{ flex: '1 1 480px' }}>
            <h1 className="chalk-title" style={{ fontSize: 92, margin: 0 }}>מערכת השעות נבנית לבד.<br />ההחלטות נשארות אצלך.</h1>
            <p style={{ fontSize: 20, lineHeight: 1.7, color: '#DDE6E0', maxWidth: 560, margin: '22px 0 30px' }}>
              משבצת בונה את מערכת השעות של בית הספר מתוך טפסי המורות, טבלת השיבוץ והכללים שלך.
              בלי התנגשויות, עם המכוון המלא, וכל פשרה מגיעה אלייך עם האפשרויות.
            </p>
            <div className="row" style={{ gap: 12 }}>
              <button className="btn pencil" style={{ fontSize: 17, padding: '14px 26px' }} onClick={onLogin}>כניסה למערכת</button>
              <a href="#how" className="btn chalk-outline" style={{ textDecoration: 'none', fontSize: 17, padding: '12px 22px' }}>איך זה עובד</a>
            </div>
          </div>
          <div aria-hidden style={{ flex: '1 1 340px', maxWidth: 420 }}>
            <div className="sticky tilt-r" style={{ color: 'var(--ink)', padding: '24px 22px 20px' }}>
              <div className="chalk-title" style={{ fontSize: 32 }}>יום רביעי חופשי</div>
              <p style={{ margin: '6px 0 12px', fontSize: 15, lineHeight: 1.6 }}>שלוש מורות ביקשו את יום רביעי. אפשר לתת אותו רק לשתיים.</p>
              <div className="btn option" style={{ marginBottom: 8 }}>רביעי לשטרן ולפרידמן · ברגר עוברת לחמישי</div>
              <div className="btn option">רביעי לברגר ולפרידמן · שטרן עוברת לשני</div>
            </div>
          </div>
        </div>
      </section>

      {/* ----- שלוש הבטחות ----- */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '60px 28px 20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 28 }}>
          {[
            { icon: <Check size={26} color="#2E4A3D" />, t: 'מדויקת', d: 'אין מורה בשתי כיתות באותה שעה, אין חדר תפוס פעמיים, והמכוון מתקיים עד השעה האחרונה. את זה מבטיח אלגוריתם, לא בדיקה ידנית.' },
            { icon: <Pencil size={26} color="#2E4A3D" />, t: 'בלי עבודה כפולה', d: 'המורות ממלאות את הטופס בעצמן. הכללים ועמודות השיבוץ נשמרים משנה לשנה, ומשנים רק את מה שהשתנה.' },
            { icon: <Bell size={26} />, t: 'את מחליטה', d: 'כשאי אפשר לקיים הכול, משבצת לא בוחרת בשקט. היא מציגה לך את הפשרה, את האפשרויות ואת המחיר של כל אחת.' },
          ].map(f => (
            <div key={f.t} className="card" style={{ padding: '22px 22px 20px' }}>
              <div style={{ color: 'var(--chalk)' }}>{f.icon}</div>
              <h2 className="chalk-title" style={{ fontSize: 38, margin: '6px 0 4px' }}>{f.t}</h2>
              <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.7 }}>{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ----- איך זה עובד ----- */}
      <section id="how" style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 28px 70px' }}>
        <h2 className="chalk-title" style={{ fontSize: 58, margin: '0 0 30px' }}>איך זה עובד</h2>
        <div style={{ paddingTop: 4 }}>
          <div className="ruler" aria-hidden />
          <ol className="steps" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
            {[
              ['המורות ממלאות טופס', 'יום חופשי, מקצועות, ובקשות במילים שלהן'],
              ['את מגדירה', 'מי מלמדת מה, וכללי בית הספר'],
              ['משבצת בונה', 'מערכת שלמה, בתוך דקות'],
              ['את מחליטה ומפרסמת', 'על כל פשרה, ואז כל מורה רואה את המערכת שלה'],
            ].map(([t, d], i) => (
              <li key={t}>
                <span className="dot done">{i + 1}</span>
                <span style={{ fontSize: 18, fontWeight: 800, marginTop: 8 }}>{t}</span>
                <span className="muted" style={{ fontSize: 15 }}>{d}</span>
              </li>
            ))}
          </ol>
        </div>
        <div style={{ textAlign: 'center', marginTop: 50 }}>
          <button className="btn" style={{ fontSize: 17, padding: '14px 28px' }} onClick={onLogin}>כניסה למערכת</button>
        </div>
      </section>

      <footer className="row muted" style={{ justifyContent: 'center', gap: 8, padding: '20px', borderTop: '1px solid var(--card-border)', fontSize: 14 }}>
        <Book size={18} /> משבצת · מערכת שעות לבתי ספר
      </footer>
    </div>
  )
}
