// Types mirror the FastAPI response model in src/api.py.
import { mockAsk } from './mock.ts'

export type Mode = 'research' | 'scoped'
export type AnswerSource = 'knowledge_base' | 'web' | 'none'

export interface Source {
  index: number
  url: string
  title: string
  snippet: string
}

export interface Grade {
  source: string
  grade: 'yes' | 'no'
}

export type Step =
  | { step: 'retrieve'; query: string; found: number }
  | { step: 'grade_documents'; kept: number; grades: Grade[] }
  | { step: 'rewrite'; new_query: string }
  | { step: 'web_search'; found: number; sources: string[] }
  | { step: 'generate'; from_source: 'knowledge_base' | 'web'; refused: boolean }
  | { step: 'check'; verdict: string; grounded: boolean | null; useful: boolean | null; reason: string }
  | { step: 'give_up' }

export interface AskResponse {
  answer: string
  answer_source: AnswerSource
  refused: boolean
  mode: Mode
  sources: Source[]
  cited: number[]
  steps: Step[]
  latency_s: number
}

const API_URL: string = import.meta.env.VITE_API_URL ?? '/api'
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export async function ask(question: string, mode: Mode, signal?: AbortSignal): Promise<AskResponse> {
  if (USE_MOCK) return mockAsk(question, mode)

  const res = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, mode }),
    signal,
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail) detail = JSON.stringify(body.detail)
    } catch {
      // error body was not JSON; keep the status text
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function checkHealth(): Promise<boolean> {
  if (USE_MOCK) return true
  try {
    const res = await fetch(`${API_URL}/health`)
    return res.ok
  } catch {
    return false
  }
}
