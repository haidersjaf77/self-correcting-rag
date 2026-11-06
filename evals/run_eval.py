"""Run the eval questions through each pipeline and save raw results (one JSON line per question x pipeline).

Resumable: re-running with the same --out skips pairs that are already done, so a crash
or Ctrl+C after an hour loses nothing.

    python -m evals.run_eval                              # all pipelines, all questions
    python -m evals.run_eval --pipelines naive --limit 3  # quick smoke test
    python -m evals.run_eval --out evals/results/run1.jsonl
"""
import argparse
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from src.components import REFUSAL
from src.graph import ask, build_graph
from src.naive import naive_ask

EVAL_DIR = Path(__file__).resolve().parent


def count_llm_calls(steps: list[dict]) -> int:
    n = 0
    for s in steps:
        if s["step"] in ("route", "rewrite", "generate"):
            n += 1
        elif s["step"] == "grade_documents":
            n += len(s["grades"])
        elif s["step"] == "check":
            n += 0 if s.get("grounded") is None else (1 if s["grounded"] is False else 2)
    return n


def run_one(pipeline: str, question: str, graphs: dict) -> dict:
    start = time.perf_counter()
    result = naive_ask(question) if pipeline == "naive" else ask(question, graphs[pipeline])
    latency = time.perf_counter() - start

    answer = result["generation"]
    refused = answer.strip() == REFUSAL
    docs = result.get("documents", [])
    steps = result.get("steps", [])
    return {
        "answer": answer,
        "refused": refused,
        "answer_source": result.get("answer_source", "none"),
        "sources": [d.metadata.get("source", "unknown") for d in docs],
        "cited": sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(docs)}),
        "contexts": [d.page_content for d in docs],      # kept for judge-based metrics later
        "steps": steps,
        "self_corrections": sum(1 for s in steps if s["step"] in ("rewrite", "web_search")),
        "llm_calls": count_llm_calls(steps),
        "latency_s": round(latency, 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipelines", nargs="+", default=["naive", "research", "scoped"],
                        choices=["naive", "research", "scoped"])
    parser.add_argument("--questions", default=str(EVAL_DIR / "questions.jsonl"))
    parser.add_argument("--limit", type=int, help="only the first N questions")
    parser.add_argument("--ids", nargs="+", help="only these question ids")
    parser.add_argument("--out", default=str(EVAL_DIR / "results" / f"run-{datetime.now():%Y%m%d-%H%M}.jsonl"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    questions = [json.loads(l) for l in open(args.questions) if l.strip()]
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]
    if args.limit:
        questions = questions[: args.limit]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in open(out):
            r = json.loads(line)
            done.add((r["id"], r["pipeline"]))

    graphs = {p: build_graph(allow_web_fallback=(p == "research"))
              for p in args.pipelines if p != "naive"}
    todo = [(q, p) for q in questions for p in args.pipelines if (q["id"], p) not in done]
    print(f"{len(todo)} runs to do ({len(done)} already in {out})")

    for i, (q, p) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {p:<8} {q['id']:<10} {q['question'][:60]}", flush=True)
        record = {"id": q["id"], "category": q["category"], "pipeline": p, "question": q["question"],
                  "timestamp": datetime.now().isoformat(timespec="seconds")}
        try:
            record.update(run_one(p, q["question"], graphs))
            print(f"           -> {'REFUSED' if record['refused'] else record['answer_source']}"
                  f" in {record['latency_s']}s", flush=True)
        except Exception as e:  # record the failure and keep going
            record["error"] = f"{type(e).__name__}: {e}"
            print(f"           -> ERROR {record['error']}", flush=True)
        with open(out, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nDone. Results in {out}\nReport: python -m evals.report {out}")


if __name__ == "__main__":
    main()
