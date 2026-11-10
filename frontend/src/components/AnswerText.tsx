import type { Source } from '../api.ts'

// Renders the answer, turning citations like [2] into links to source 2.
export function AnswerText({ text, sources }: { text: string; sources: Source[] }) {
  const byIndex = new Map(sources.map((s) => [s.index, s]))
  const parts = text.split(/(\[\d+\])/g)

  return (
    <p className="leading-relaxed">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/)
        const src = m ? byIndex.get(Number(m[1])) : undefined
        if (!m || !src) return <span key={i}>{part}</span>
        return (
          <a
            key={i}
            href={src.url}
            target="_blank"
            rel="noreferrer"
            title={src.title || src.url}
            className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-indigo-100 px-1 align-text-top text-xs font-semibold text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-500/20 dark:text-indigo-300 dark:hover:bg-indigo-500/30"
          >
            {m[1]}
          </a>
        )
      })}
    </p>
  )
}
