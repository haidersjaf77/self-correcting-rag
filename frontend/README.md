# Self-Correcting RAG: web UI

React + TypeScript + Tailwind, built with Vite. Talks to the FastAPI backend (`src/api.py`).

```bash
npm install
npm run dev          # http://localhost:5173 (needs the API on :8000)
VITE_USE_MOCK=true npm run dev   # sample responses, no backend needed
npm run build        # production build in dist/
```
