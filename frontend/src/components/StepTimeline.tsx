import type { ReactNode } from 'react'
import type { Step } from '../api.ts'
import { domain } from './utils.ts'

type Tone = 'neutral' | 'good' | 'bad' | 'warn'

const DOT: Record<Tone, string> = {
  neutral: 'bg-zinc-400 dark:bg-zinc-500',
  good: 'bg-emerald-500',
  bad: 'bg-rose-500',
  warn: 'bg-amber-500',
}

function describe(s: Step): { title: string; tone: Tone; body?: ReactNode } {
  switch (s.step) {
    case 'retrieve':
      return { title: `Retrieve ${s.found} chunks`, tone: 'neutral', body: <code className="text-xs">{s.query}</code> }
    case 'grade_documents':
      return {
        title: `Grade chunks: kept ${s.kept} of ${s.grades.length}`,
        tone: s.kept > 0 ? 'good' : 'bad',
        body: (
          <ul className="mt-1 space-y-0.5 text-xs">
            {s.grades.map((g, i) => (
              <li key={i} className={g.grade === 'yes' ? 'text-emerald-700 dark:text-emerald-400' : 'text-zinc-500'}>
                {g.grade === 'yes' ? '✓ relevant' : '✗ not relevant'} · {domain(g.source)}
              </li>
            ))}
          </ul>
        ),
      }
    case 'rewrite':
      return { title: 'Rewrite the search query', tone: 'warn', body: <code className="text-xs">{s.new_query}</code> }
    case 'web_search':
      return {
        title: `Search the web: ${s.found} results`,
        tone: 'warn',
        body: <span className="text-xs text-zinc-500">{s.sources.map(domain).join(', ')}</span>,
      }
    case 'generate':
      return {
        title: `Generate an answer from the ${s.from_source === 'web' ? 'web results' : 'knowledge base'}`,
        tone: s.refused ? 'bad' : 'neutral',
        body: s.refused ? <span className="text-xs text-zinc-500">The model found no answer in the documents.</span> : undefined,
      }
    case 'check': {
      const passed = s.verdict === 'done'
      const problem = s.grounded === false ? 'not grounded in the documents' : 'does not answer the question'
      return {
        title: passed ? 'Check passed: grounded and answers the question' : `Check failed (${problem}): ${s.verdict.replace('_', ' ')}`,
        tone: passed ? 'good' : 'bad',
        body: s.reason ? <span className="text-xs text-zinc-500">{s.reason}</span> : undefined,
      }
    }
    case 'give_up':
      return { title: 'Give up: refuse rather than return an unverified answer', tone: 'warn' }
  }
}

export function StepTimeline({ steps }: { steps: Step[] }) {
  return (
    <ol className="relative space-y-3 border-l border-zinc-200 pl-5 dark:border-zinc-800">
      {steps.map((s, i) => {
        const d = describe(s)
        return (
          <li key={i} className="relative">
            <span className={`absolute -left-[25px] top-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-white dark:ring-zinc-900 ${DOT[d.tone]}`} />
            <div className="text-sm font-medium">{d.title}</div>
            {d.body && <div className="mt-0.5 break-words">{d.body}</div>}
          </li>
        )
      })}
    </ol>
  )
}
