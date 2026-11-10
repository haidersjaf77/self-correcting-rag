// Sample responses for building the UI without calling the API (VITE_USE_MOCK=true).
// Taken from real runs of the graph.
import type { AskResponse, Mode } from './api.ts'

const REFUSAL =
  "Sorry, I couldn't find information about that in my knowledge base, so I'm not able to answer it reliably. " +
  'Feel free to ask about AI agents, context engineering, LLM reasoning, or evaluation.'

const answered: AskResponse = {
  answer:
    'AI agents manage memory and context by dynamically retrieving information at runtime and maintaining a "just in time" approach to context, which involves supplementing the model\'s context with a memory system to handle information that exceeds the model\'s context limit [2]. Context engineering is also crucial, as it involves curating the limited context window from an evolving universe of information, treating context as a finite resource with diminishing marginal returns [4].',
  answer_source: 'knowledge_base',
  refused: false,
  mode: 'research',
  sources: [
    { index: 1, url: 'https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents', title: 'Effective context engineering for AI agents \\ Anthropic', snippet: "components of context (system prompts, tools, examples, message history, etc) is to be thoughtful and keep your context informative, yet tight. Now let's dive into dynamically retrieving context at runtime." },
    { index: 2, url: 'https://huyenchip.com/2025/01/07/agents.html', title: 'Agents', snippet: 'The agentic pattern often deals with information that exceeds a model’s context limit. A memory system that supplements the model’s context in handling information...' },
    { index: 3, url: 'https://www.anthropic.com/news/contextual-retrieval', title: 'Contextual retrieval in AI systems \\ Anthropic', snippet: 'A primer on RAG: scaling to larger knowledge bases. Introducing Contextual Retrieval...' },
    { index: 4, url: 'https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents', title: 'Effective context engineering for AI agents \\ Anthropic', snippet: 'An agent running in a loop generates more and more data that could be relevant for the next turn of inference, and this information must be cyclically refined.' },
  ],
  cited: [2, 4],
  steps: [
    { step: 'retrieve', query: 'How do AI agents manage memory and context?', found: 4 },
    { step: 'grade_documents', kept: 4, grades: [
      { source: 'https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents', grade: 'yes' },
      { source: 'https://huyenchip.com/2025/01/07/agents.html', grade: 'yes' },
      { source: 'https://www.anthropic.com/news/contextual-retrieval', grade: 'yes' },
      { source: 'https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents', grade: 'yes' },
    ] },
    { step: 'generate', from_source: 'knowledge_base', refused: false },
    { step: 'check', verdict: 'done', grounded: true, useful: true, reason: "All claims are supported: 'just in time' context strategies [1], information exceeding the context limit [2], and context as a finite resource [4]." },
  ],
  latency_s: 12.4,
}

const selfCorrected: AskResponse = {
  answer: 'Reward hacking exists because reinforcement-learning environments are typically imperfect and it is fundamentally hard to write a reward function that exactly captures the intended behavior [1][2].',
  answer_source: 'knowledge_base',
  refused: false,
  mode: 'research',
  sources: [
    { index: 1, url: 'https://lilianweng.github.io/posts/2024-11-28-reward-hacking/', title: 'Reward Hacking in Reinforcement Learning | Lil\'Log', snippet: 'Reward hacking exists because RL environments are often imperfect, and it is fundamentally challenging to accurately specify a reward function.' },
    { index: 2, url: 'https://lilianweng.github.io/posts/2024-11-28-reward-hacking/', title: 'Reward Hacking in Reinforcement Learning | Lil\'Log', snippet: 'Garrabrant (2017) categorized Goodhart’s law into 4 variants...' },
  ],
  cited: [1, 2],
  steps: [
    { step: 'retrieve', query: 'Why does reward hacking exist, according to Lilian Weng?', found: 4 },
    { step: 'grade_documents', kept: 1, grades: [
      { source: 'https://huyenchip.com/2025/01/07/agents.html', grade: 'no' },
      { source: 'https://hamel.dev/blog/posts/evals-faq/', grade: 'no' },
      { source: 'https://lilianweng.github.io/posts/2024-11-28-reward-hacking/', grade: 'yes' },
      { source: 'https://huyenchip.com/2025/01/07/agents.html', grade: 'no' },
    ] },
    { step: 'generate', from_source: 'knowledge_base', refused: false },
    { step: 'check', verdict: 'rewrite', grounded: true, useful: false, reason: 'Grounded, but it does not resolve the question.' },
    { step: 'rewrite', new_query: 'causes of reward hacking reward function specification' },
    { step: 'retrieve', query: 'causes of reward hacking reward function specification', found: 4 },
    { step: 'grade_documents', kept: 2, grades: [
      { source: 'https://lilianweng.github.io/posts/2024-11-28-reward-hacking/', grade: 'yes' },
      { source: 'https://lilianweng.github.io/posts/2024-11-28-reward-hacking/', grade: 'yes' },
      { source: 'https://hamel.dev/blog/posts/evals-faq/', grade: 'no' },
      { source: 'https://lilianweng.github.io/posts/2025-05-01-thinking/', grade: 'no' },
    ] },
    { step: 'generate', from_source: 'knowledge_base', refused: false },
    { step: 'check', verdict: 'done', grounded: true, useful: true, reason: 'Both reasons are stated in the documents.' },
  ],
  latency_s: 21.7,
}

const refused: AskResponse = {
  answer: REFUSAL,
  answer_source: 'none',
  refused: true,
  mode: 'scoped',
  sources: [],
  cited: [],
  steps: [
    { step: 'retrieve', query: 'Who won the 2022 FIFA World Cup?', found: 4 },
    { step: 'grade_documents', kept: 0, grades: [
      { source: 'https://hamel.dev/blog/posts/evals-faq/', grade: 'no' },
      { source: 'https://huyenchip.com/2025/01/07/agents.html', grade: 'no' },
      { source: 'https://lilianweng.github.io/posts/2024-11-28-reward-hacking/', grade: 'no' },
      { source: 'https://www.anthropic.com/engineering/building-effective-agents', grade: 'no' },
    ] },
    { step: 'rewrite', new_query: '2022 FIFA World Cup winner' },
    { step: 'retrieve', query: '2022 FIFA World Cup winner', found: 4 },
    { step: 'grade_documents', kept: 0, grades: [
      { source: 'https://hamel.dev/blog/posts/evals-faq/', grade: 'no' },
      { source: 'https://huyenchip.com/2025/01/07/agents.html', grade: 'no' },
      { source: 'https://lilianweng.github.io/posts/2025-05-01-thinking/', grade: 'no' },
      { source: 'https://www.anthropic.com/news/contextual-retrieval', grade: 'no' },
    ] },
    { step: 'give_up' },
  ],
  latency_s: 6.2,
}

export async function mockAsk(question: string, mode: Mode): Promise<AskResponse> {
  await new Promise((r) => setTimeout(r, 1200))
  const q = question.toLowerCase()
  const base = q.includes('reward') ? selfCorrected : q.includes('world cup') || q.includes('biryani') ? refused : answered
  return { ...base, mode }
}
