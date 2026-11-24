import { useEffect, useState } from 'react'
import { api } from './api'
import { Pencil } from './icons'
import Assignment from './pages/Assignment'
import Dashboard from './pages/Dashboard'
import Forms from './pages/Forms'
import Home from './pages/Home'
import Login, { type User } from './pages/Login'
import Rules from './pages/Rules'
import SchoolData from './pages/SchoolData'
import TeacherView from './pages/TeacherView'
import Workspace from './pages/Workspace'
import type { Run, School } from './types'

const TABS = [
  { id: 'dash', label: 'לוח בקרה', color: '#F2C14E' },
  { id: 'forms', label: 'טפסי מורות', color: '#D8C3E6' },
  { id: 'assign', label: 'שיבוץ', color: '#A9CBE3' },
  { id: 'rules', label: 'כללים', color: '#E9B8A6' },
  { id: 'work', label: 'בניית המערכת', color: '#B7D3B0' },
  { id: 'school', label: 'בית הספר', color: '#C9D6EA' },
]

export default function App() {
  const [school, setSchool] = useState<School | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [screen, setScreen] = useState<'home' | 'login' | 'app'>('home')
  const [user, setUser] = useState<User | null>(null)
  const [tab, setTab] = useState('dash')
  const [run, setRun] = useState<Run | null>(null)

  const loadSchool = () => api.school().then(setSchool).catch(e => setError(e.message))
  // טוענים מחדש בכל מעבר מסך, כדי שטופס שמורה שלחה יופיע מיד אצל המנהלת
  useEffect(() => { loadSchool() }, [tab, user])

  const login = (u: User) => { setUser(u); setTab('dash'); setScreen('app') }
  const logout = () => { setUser(null); setScreen('home') }

  return (
    <>
      <header className="board">
        <button className="brand" onClick={() => setScreen(user ? 'app' : 'home')}
          style={{ background: 'none', border: 0, color: 'inherit', cursor: 'pointer', padding: 0 }}>
          <Pencil size={34} color="#F2C14E" />
          <span className="chalk-title name">משבצת</span>
          {user && <small>[שם בית הספר] · תשפ"ז</small>}
        </button>

        {screen === 'app' && user?.role === 'principal' && (
          <nav className="tabs" aria-label="ניווט ראשי">
            {TABS.map(t => (
              <button key={t.id} className={`tab ${tab === t.id ? 'active' : ''}`} style={{ background: t.color }}
                aria-current={tab === t.id ? 'page' : undefined} onClick={() => setTab(t.id)}>{t.label}</button>
            ))}
          </nav>
        )}

        <div className="side">
          {user ? (
            <>
              <span style={{ fontSize: 15, color: '#DDE6E0' }}>
                {user.role === 'principal' ? 'שלום, המנהלת' : `שלום, גב' ${user.name}`}
              </span>
              <button className="btn chalk-outline" style={{ padding: '8px 14px', minHeight: 40, fontSize: 14 }} onClick={logout}>יציאה</button>
            </>
          ) : screen === 'home' && (
            <button className="btn pencil" onClick={() => setScreen('login')}>כניסה</button>
          )}
        </div>
      </header>

      {school && !school.llm && screen === 'app' && (
        <div className="banner">
          מצב הדגמה: אין מפתח למודל שפה, ולכן ההבנה של טקסט חופשי פשוטה ומוגבלת.
        </div>
      )}

      {error && <div className="page"><div className="sticky">לא הצלחתי להתחבר לשרת: {error}</div></div>}

      {screen === 'home' && <Home onLogin={() => setScreen('login')} />}
      {screen === 'login' && school && <Login school={school} onLogin={login} onBack={() => setScreen('home')} />}

      {screen === 'app' && school && user?.role === 'teacher' && (
        <TeacherView school={school} run={run} me={user.name} onSaved={loadSchool} />
      )}
      {screen === 'app' && school && user?.role === 'principal' && (
        <main>
          {tab === 'dash' && <Dashboard school={school} run={run} go={setTab} />}
          {tab === 'forms' && <Forms school={school} />}
          {tab === 'assign' && <Assignment school={school} onChanged={loadSchool} />}
          {tab === 'rules' && <Rules school={school} onChanged={loadSchool} />}
          {tab === 'work' && <Workspace school={school} run={run} setRun={setRun} />}
          {tab === 'school' && <SchoolData onChanged={() => { setRun(null); loadSchool() }} />}
        </main>
      )}
    </>
  )
}
