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

export type SchoolStatus = { custom: boolean; classes: number; teachers: number; subjects: number; days: number; problems: string[] }
export type ImportResult = Partial<SchoolStatus> & { ok: boolean; errors: string[]; warnings: string[] }

export const api = {
  schoolStatus: () => call<SchoolStatus>('/api/school/status'),
  schoolImport: async (file: File): Promise<ImportResult> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/school/import', { method: 'POST', body: fd })
    if (!res.ok) throw new Error(`שגיאה ${res.status}`)
    return res.json()
  },
  schoolReset: () => call<SchoolStatus>('/api/school/reset', {}),
  school: () => call<School>('/api/school'),
  patchRule: (id: string, body: { enabled?: boolean; text?: string; params?: Record<string, number> }) =>
    call<unknown>(`/api/rules/${encodeURIComponent(id)}`, body, 'PUT'),
  patchAssignment: (cls: string, subject: string, teachers: string[]) =>
    call<{ problems: string[] }>('/api/assignment', { cls, subject, teachers }, 'PUT'),
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
