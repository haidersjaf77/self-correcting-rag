import type { AnswerSource } from '../api.ts'

const STYLES: Record<AnswerSource, { label: string; cls: string }> = {
  knowledge_base: {
    label: 'From the knowledge base',
    cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300',
  },
  web: {
    label: 'From a web search',
    cls: 'bg-sky-100 text-sky-800 dark:bg-sky-500/15 dark:text-sky-300',
  },
  none: {
    label: 'Not answered: no reliable source found',
    cls: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300',
  },
}

export function SourceBadge({ source }: { source: AnswerSource }) {
  const s = STYLES[source]
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {s.label}
    </span>
  )
}
