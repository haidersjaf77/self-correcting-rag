import { useEffect, useRef, useState } from 'react'
import { ask, checkHealth, type AskResponse, type Mode } from './api.ts'
import { AnswerCard } from './components/AnswerCard.tsx'

interface Turn {
  id: number
  question: string
  mode: Mode
  status: 'loading' | 'done' | 'error'
  data?: AskResponse
  error?: string
}

const EXAMPLES = [
  'How do AI agents manage memory and context?',
  'By how much does Contextual Retrieval reduce failed retrievals?',
  'Why does reward hacking exist?',
  'Who won the 2022 FIFA World Cup?',
]

function Elapsed() {
  const [s, setS] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setS((x) => x + 1), 1000)
    return () => clearInterval(t)
  }, [])
  return <span>{s} s</span>
}

export default function App() {
  const [mode, setMode] = useState<Mode>('research')
  const [input, setInput] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const busy = turns.some((t) => t.status === 'loading')

  useEffect(() => {
    checkHealth().then(setHealthy)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  async function submit(question: string) {
    const q = question.trim()
    if (!q || busy) return
    const id = Date.now()
    setInput('')
    setTurns((ts) => [...ts, { id, question: q, mode, status: 'loading' }])
    try {
      const data = await ask(q, mode)
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, status: 'done', data } : t)))
    } catch (e) {
      const error = e instanceof Error ? e.message : String(e)
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, status: 'error', error } : t)))
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4">
      <header className="sticky top-0 z-10 -mx-4 border-b border-zinc-200 bg-zinc-50/90 px-4 py-4 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-auto">
            <h1 className="text-lg font-semibold">Self-Correcting RAG</h1>
            <p className="text-xs text-zinc-500">
              Answers are checked for grounding. If a check fails, it rewrites the query or searches again, and
              refuses rather than guess.
            </p>
          </div>
          <div role="radiogroup" aria-label="Mode" className="flex rounded-lg bg-zinc-200/70 p-1 text-sm dark:bg-zinc-800">
            {(['research', 'scoped'] as const).map((m) => (
              <button
                key={m}
                role="radio"
                aria-checked={mode === m}
                onClick={() => setMode(m)}
                title={m === 'research' ? 'Knowledge base, with web search as a fallback' : 'Knowledge base only; never searches the web'}
                className={`rounded-md px-3 py-1 font-medium capitalize transition ${
                  mode === m ? 'bg-white shadow-sm dark:bg-zinc-950' : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
          <span className="flex items-center gap-1.5 text-xs text-zinc-500" title="FastAPI backend">
            <span
              className={`h-2 w-2 rounded-full ${healthy === null ? 'bg-zinc-400' : healthy ? 'bg-emerald-500' : 'bg-rose-500'}`}
            />
            {healthy === null ? 'checking API' : healthy ? 'API connected' : 'API offline'}
          </span>
        </div>
      </header>

      <main className="flex-1 space-y-8 py-6">
        {turns.length === 0 && (
          <div className="pt-10 text-center">
            <p className="text-sm text-zinc-500">
              Ask about AI agents, context engineering, multi-agent systems, MCP, RAG, LLM reasoning, reward hacking,
              hallucinations, or LLM evaluation.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => submit(ex)}
                  className="rounded-full border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700 hover:bg-white dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t) => (
          <section key={t.id} className="space-y-3">
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-white">{t.question}</div>
            </div>
            {t.status === 'loading' && (
              <div className="flex items-center gap-3 rounded-2xl border border-zinc-200 bg-white p-5 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-indigo-600" />
                Retrieving, grading and checking… <Elapsed />
              </div>
            )}
            {t.status === 'error' && (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
                Request failed: {t.error}
              </div>
            )}
            {t.status === 'done' && t.data && <AnswerCard data={t.data} />}
          </section>
        ))}
        <div ref={bottomRef} />
      </main>

      <footer className="sticky bottom-0 -mx-4 bg-zinc-50/90 px-4 pb-5 pt-2 backdrop-blur dark:bg-zinc-950/90">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            submit(input)
          }}
          className="flex items-end gap-2 rounded-2xl border border-zinc-300 bg-white p-2 shadow-sm focus-within:border-indigo-500 dark:border-zinc-700 dark:bg-zinc-900"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit(input)
              }
            }}
            rows={1}
            placeholder="Ask a question…"
            className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 outline-none placeholder:text-zinc-400"
          />
          <button
            type="submit"
            disabled={!input.trim() || busy}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Ask
          </button>
        </form>
        <p className="mt-2 text-center text-xs text-zinc-500">
          {mode === 'research' ? 'Research mode: web search is used only if the knowledge base has no answer.' : 'Scoped mode: knowledge base only.'}
        </p>
      </footer>
    </div>
  )
}
