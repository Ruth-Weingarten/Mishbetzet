import { useState } from 'react'
import { Pencil } from '../icons'
import type { School } from '../types'

export type User = { role: 'principal'; name: string } | { role: 'teacher'; name: string }

/* בהדגמה אין עדיין התחברות אמיתית: החשבונות קבועים, והסיסמה לכולם היא demo.
   בגרסה עם מסד נתונים זה יוחלף בהתחברות מול השרת. */
const DEMO_PASSWORD = 'demo'

export default function Login({ school, onLogin, onBack }: {
  school: School; onLogin: (u: User) => void; onBack: () => void
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const accounts: { email: string; user: User; label: string }[] = [
    { email: 'principal@demo', user: { role: 'principal', name: 'המנהלת' }, label: 'מנהלת' },
    ...school.teachers.map(t => ({ email: t.email, user: { role: 'teacher' as const, name: t.name }, label: `גב' ${t.name}` })),
  ]

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const acc = accounts.find(a => a.email === email.trim())
    if (!acc || password !== DEMO_PASSWORD) { setError('האימייל או הסיסמה לא נכונים'); return }
    onLogin(acc.user)
  }

  return (
    <div className="page" style={{ maxWidth: 980, display: 'flex', flexWrap: 'wrap', gap: 36, alignItems: 'flex-start', paddingTop: 50 }}>
      <form onSubmit={submit} className="card tape" style={{ flex: '1 1 360px', padding: '30px 28px 26px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div className="row" style={{ gap: 10 }}>
          <Pencil size={30} color="#2E4A3D" />
          <h1 className="chalk-title" style={{ margin: 0, fontSize: 54 }}>כניסה</h1>
        </div>
        <label style={{ fontWeight: 700 }}>
          אימייל
          <input type="email" dir="ltr" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username"
            style={{ display: 'block', width: '100%', marginTop: 4, fontSize: 16, padding: '8px 4px', border: 0, borderBottom: '2px solid var(--chalk)', background: 'transparent', textAlign: 'right' }} />
        </label>
        <label style={{ fontWeight: 700 }}>
          סיסמה
          <input type="password" dir="ltr" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password"
            style={{ display: 'block', width: '100%', marginTop: 4, fontSize: 16, padding: '8px 4px', border: 0, borderBottom: '2px solid var(--chalk)', background: 'transparent', textAlign: 'right' }} />
        </label>
        {error && <p role="alert" style={{ margin: 0, color: '#8A2E0B', fontWeight: 700 }}>{error}</p>}
        <button className="btn" type="submit" style={{ fontSize: 16 }}>כניסה</button>
        <button type="button" className="btn ghost" onClick={onBack}>חזרה לדף הבית</button>
      </form>

      <aside className="sticky tilt-r" style={{ flex: '1 1 300px', maxWidth: 380 }}>
        <h2 className="chalk-title" style={{ margin: '0 0 6px', fontSize: 34 }}>חשבונות להדגמה</h2>
        <p style={{ margin: '0 0 10px', fontSize: 14, lineHeight: 1.6 }}>
          לחיצה על חשבון ממלאת את הפרטים. הסיסמה לכולם: <strong dir="ltr">demo</strong>
        </p>
        <button type="button" className="btn option" style={{ marginBottom: 8 }}
          onClick={() => { setEmail('principal@demo'); setPassword(DEMO_PASSWORD); setError(null) }}>
          כניסה כמנהלת
        </button>
        <label style={{ display: 'block', fontSize: 14, fontWeight: 700, marginTop: 8 }}>
          או כמורה:
          <select className="underline" style={{ width: '100%' }} defaultValue=""
            onChange={e => { setEmail(e.target.value); setPassword(DEMO_PASSWORD); setError(null) }}>
            <option value="" disabled>בחירת מורה</option>
            {accounts.filter(a => a.user.role === 'teacher').map(a => <option key={a.email} value={a.email}>{a.label}</option>)}
          </select>
        </label>
      </aside>
    </div>
  )
}
