import type { Form, Run, School } from './types'

async function call<T>(url: string, body?: unknown, method = 'POST'): Promise<T> {
  const res = await fetch(url, body === undefined ? undefined : {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `שגיאה ${res.status}`)
  }
  return res.json()
}

export const api = {
  school: () => call<School>('/api/school'),
  startRun: () => call<Run>('/api/runs', {}),
  resume: (id: string, value: unknown) => call<Run>(`/api/runs/${id}/resume`, { value }),
  teacherTranslate: (teacher: string, text: string) =>
    call<{ thread: string; proposal: { matched: boolean; summary: string } }>('/api/teacher/translate', { teacher, text }),
  forms: () => call<{ teacher: string; hours: number; form: Form | null }[]>('/api/forms'),
  myForm: (t: string) => call<Form>(`/api/forms/${encodeURIComponent(t)}`),
  saveForm: (t: string, f: Form) => call<Form>(`/api/forms/${encodeURIComponent(t)}`, f, 'PUT'),
  teacherConfirm: (thread: string, ok: boolean) =>
    call<{ confirmed: boolean }>(`/api/teacher/${thread}/confirm`, { ok }),
}
