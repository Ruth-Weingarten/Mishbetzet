import { Check, Pencil } from '../icons'
import type { School } from '../types'

export default function Rules({ school }: { school: School }) {
  return (
    <div className="page" style={{ display: 'flex', flexWrap: 'wrap', gap: 32, alignItems: 'flex-start' }}>
      <section style={{ flex: '999 1 560px', minWidth: 0 }}>
        <div className="page-head">
          <div>
            <h1 className="chalk-title" style={{ fontSize: 62 }}>כללי בית הספר</h1>
            <p>נשמרו מתשפ"ו. המערכת תנסה לקיים את כולם, וכשאי אפשר, תשאל אותך.</p>
          </div>
        </div>
        <ul className="card" style={{ listStyle: 'none', margin: 0, padding: '10px 20px',
          backgroundImage: 'repeating-linear-gradient(to bottom, transparent 0, transparent 63px, var(--line) 63px, var(--line) 64px)' }}>
          {school.rules.map(r => (
            <li key={r.id} className="row" style={{ height: 64, gap: 14, flexWrap: 'nowrap' }}>
              <span className="check" aria-hidden><Check size={22} /></span>
              <span style={{ flex: 1, fontSize: 16, fontWeight: 700 }}>{r.text}</span>
              <button className="send" aria-label="עריכת הכלל" style={{ background: 'transparent', boxShadow: 'none', color: 'var(--chalk)' }}><Pencil size={20} /></button>
            </li>
          ))}
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
