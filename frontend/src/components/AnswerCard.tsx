import type { AskResponse } from '../api.ts'
import { AnswerText } from './AnswerText.tsx'
import { SourceBadge } from './SourceBadge.tsx'
import { SourceList } from './SourceList.tsx'
import { StepTimeline } from './StepTimeline.tsx'

export function AnswerCard({ data }: { data: AskResponse }) {
  const corrections = data.steps.filter((s) => s.step === 'rewrite' || s.step === 'web_search').length

  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-wrap items-center gap-2">
        <SourceBadge source={data.answer_source} />
        {corrections > 0 && (
          <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-medium text-violet-800 dark:bg-violet-500/15 dark:text-violet-300">
            {corrections} self-correction{corrections > 1 ? 's' : ''}
          </span>
        )}
        <span className="ml-auto text-xs text-zinc-500">
          {data.latency_s.toFixed(1)} s · {data.mode} mode
        </span>
      </div>

      <AnswerText text={data.answer} sources={data.sources} />

      {data.sources.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
            Sources ({data.cited.length} cited of {data.sources.length} used)
          </summary>
          <div className="mt-3">
            <SourceList sources={data.sources} cited={data.cited} />
          </div>
        </details>
      )}

      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
          How this answer was produced ({data.steps.length} steps)
        </summary>
        <div className="mt-3 pl-1">
          <StepTimeline steps={data.steps} />
        </div>
      </details>
    </div>
  )
}
