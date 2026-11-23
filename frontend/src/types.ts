export type Group = 'kodesh' | 'lang' | 'math' | 'science' | 'other'

export interface Form {
  free_day: string | null
  alt_day: string | null
  subjects: string[]
  blocked_class: string | null
  reason: string
  leave: boolean
  leave_when: string
  reduce_hours: number
  free_text: string
  confirmed_rule?: { matched: boolean; summary: string } | null
  submitted?: boolean
}

export interface Teacher {
  name: string
  role: string | null
  email: string
  hours: number
  form: Form | null
  blocked: string[]
}

export interface AssignmentCell {
  cls: string
  subject: string
  kind: 'fixed' | 'pool' | 'parallel'
  teachers: string[]
  homeroom?: boolean
  block?: string | null      // הקבצה: כמה כיתות באותה שעה
  pullout?: boolean          // שיעור סיוע במקביל לשיעור אחר
}

export interface Rule { id: string; kind: string; params: Record<string, unknown>; text: string; enabled?: boolean }

export interface School {
  days: string[]
  periodsPerDay: number[]
  periodTimes: [string, string][]
  subjects: Record<string, Group>
  curriculum: Record<string, number>
  classCurriculum: Record<string, Record<string, number>>
  classes: string[]
  grades: string[]
  homeroom: Record<string, string>
  teachers: Teacher[]
  assignment: AssignmentCell[]
  rules: Rule[]
  notes: { id: string; text: string }[]
  problems: string[]
  llm: boolean
}

export interface Lesson {
  cls: string
  subject: string
  teachers: string[]
  day: number
  period: number
  room: string | null
  group: Group
  pullout?: boolean
}

export interface Instance { key: string; label: string }

export interface Option { id: string; label: string; impact?: string; disabled?: boolean }

export interface Conflict {
  id: string
  text: string
  kind: string
  instances: Instance[]
  explanation: string
  options: Option[]
}

export interface Proposal {
  id: string
  source: string
  original: string
  matched: boolean
  kind: string | null
  params: Record<string, unknown>
  summary: string
}

export type Waiting =
  | { type: 'review'; items: Proposal[] }
  | { type: 'decision'; conflicts: Conflict[] }
  | { type: 'clarify'; question: string }
  | { type: 'confirm'; summary: string; moved: number; added: { text: string; count: number }[] }

export interface ChatMsg { role: 'system' | 'principal'; text: string }

export interface Run {
  id: string
  waiting: Waiting | null
  round: number
  published: boolean
  lessons: Lesson[]
  conflicts: Conflict[]
  chat: ChatMsg[]
}
