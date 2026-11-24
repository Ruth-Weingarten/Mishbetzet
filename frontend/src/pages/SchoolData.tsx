import { useEffect, useRef, useState } from 'react'
import { api, type ImportResult, type SchoolStatus } from '../api'

// בית הספר: הורדת תבנית אקסל, ייבוא נתוני בית ספר אחר, וחזרה לנתוני ההדגמה
export default function SchoolData({ onChanged }: { onChanged: () => void }) {
  const [status, setStatus] = useState<SchoolStatus | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)

  const load = () => api.schoolStatus().then(setStatus).catch(e => setError(e.message))
  useEffect(() => { load() }, [])

  const upload = async () => {
    const file = input.current?.files?.[0]
    if (!file) { setError('צריך לבחור קובץ אקסל קודם.'); return }
    setBusy(true); setError(''); setResult(null)
    try {
      const r = await api.schoolImport(file)
      setResult(r)
      if (r.ok) { await load(); onChanged() }
    } catch (e) { setError((e as Error).message) }
    setBusy(false)
  }

  const reset = async () => {
    setBusy(true); setError(''); setResult(null)
    try { await api.schoolReset(); await load(); onChanged() } catch (e) { setError((e as Error).message) }
    setBusy(false)
  }

  return (
    <div className="page" style={{ maxWidth: 820 }}>
      <div className="page-head">
        <div>
          <h1 className="chalk-title" style={{ fontSize: 62 }}>בית הספר</h1>
          <p>כאן מגדירים את בית הספר: כיתות, מורות, מקצועות, שעות וימי לימוד.</p>
        </div>
      </div>

      {status && (
        <div className="sticky" style={{ marginBottom: 20, lineHeight: 1.7 }}>
          {status.custom ? 'בית ספר שיובא מקובץ' : 'נתוני ההדגמה (בית ספר בית יעקב, כיתות א׳–ח׳)'}
          : {status.classes} כיתות, {status.teachers} מורות, {status.subjects} מקצועות, {status.days} ימי לימוד.
          {status.problems.map(p => <div key={p} style={{ color: '#8A2B0C' }}>{p}</div>)}
        </div>
      )}

      <h2 style={{ fontSize: 24 }}>שלב 1: מורידים תבנית</h2>
      <p>קובץ אקסל עם הוראות ודוגמה. ממלאים בו את הימים והשיעורים בכל יום, את הכיתות, המורות והשיעורים.</p>
      <p><a className="btn pencil" href="/api/school/template" download>הורדת תבנית אקסל</a></p>

      <h2 style={{ fontSize: 24, marginTop: 28 }}>שלב 2: מעלים את הקובץ המלא</h2>
      <p>הנתונים הנוכחיים יוחלפו, וטפסי המורות והכללים הספציפיים של בית הספר הקודם יימחקו. המערכת תתחיל מחדש.</p>
      <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
        <input ref={input} type="file" accept=".xlsx" aria-label="קובץ אקסל" style={{ fontSize: 15 }} />
        <button className="btn pencil" disabled={busy} onClick={upload}>{busy ? 'בודקת…' : 'העלאה'}</button>
      </div>

      {error && <div role="alert" className="sticky" style={{ marginTop: 16 }}>{error}</div>}

      {result && !result.ok && (
        <div role="alert" style={{ marginTop: 16, border: '2px solid #D9532C', background: '#FBE7DF', borderRadius: 6, padding: '12px 16px' }}>
          <strong>הקובץ לא הועלה. צריך לתקן:</strong>
          <ul style={{ margin: '8px 0 0', paddingInlineStart: 22, lineHeight: 1.7 }}>
            {result.errors.map(e => <li key={e}>{e}</li>)}
          </ul>
        </div>
      )}
      {result?.ok && (
        <div className="sticky" style={{ marginTop: 16, lineHeight: 1.7 }}>
          הקובץ נטען: {result.classes} כיתות, {result.teachers} מורות, {result.subjects} מקצועות.
          אפשר לעבור ללשונית "בניית המערכת" ולבנות.
          {result.warnings?.map(w => <div key={w}>{w}</div>)}
        </div>
      )}

      {status?.custom && (
        <p style={{ marginTop: 32 }}>
          <button className="btn chalk-outline" disabled={busy} onClick={reset}>חזרה לנתוני ההדגמה</button>
        </p>
      )}
    </div>
  )
}
