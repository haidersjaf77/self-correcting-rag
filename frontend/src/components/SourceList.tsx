import type { Source } from '../api.ts'
import { cleanTitle, domain } from './utils.ts'

export function SourceList({ sources, cited }: { sources: Source[]; cited: number[] }) {
  return (
    <ol className="space-y-3">
      {sources.map((s) => {
        const isCited = cited.includes(s.index)
        return (
          <li key={s.index} className="flex gap-3">
            <span
              className={`mt-0.5 flex h-5 min-w-5 items-center justify-center rounded text-xs font-semibold ${
                isCited
                  ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300'
                  : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400'
              }`}
            >
              {s.index}
            </span>
            <div className="min-w-0">
              <a href={s.url} target="_blank" rel="noreferrer" className="font-medium hover:underline">
                {cleanTitle(s.title, s.url)}
              </a>
              <span className="ml-2 text-xs text-zinc-500">
                {domain(s.url)} · {isCited ? 'cited' : 'used, not cited'}
              </span>
              <p className="mt-1 line-clamp-2 text-sm text-zinc-600 dark:text-zinc-400">{s.snippet}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
