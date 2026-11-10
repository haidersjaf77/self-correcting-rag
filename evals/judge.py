"""LLM-as-a-judge: score saved answers against the reference answers.

Two binary verdicts per answer (pass/fail is easier to make consistent than a 1-5 scale):
  correct   no claim in the answer contradicts or misstates the reference
  complete  the answer covers the reference's main points

Runs on an existing results file (never re-runs the pipelines) and writes <results>.judged.jsonl.
Resumable: already-judged rows are skipped.

    python -m evals.judge evals/results/full-groq-1.jsonl
    python -m evals.report evals/results/full-groq-1.judged.jsonl

The judge uses JUDGE_MODEL (default qwen/qwen3.8-27b), a different model family from the
pipeline's gpt-oss, so it isn't grading its own work. Before trusting it, spot-check ~10
verdicts by hand: a judge is only as good as its agreement with a human.
"""
import argparse
import json
from pathlib import Path
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src import config
from src.components import make_llm

EVAL_DIR = Path(__file__).resolve().parent
JUDGED_CATEGORIES = {"in_corpus", "vague", "cross_topic", "out_of_scope"}  # the ones with a real reference answer


class Verdict(BaseModel):
    reasoning: str = Field(description="Compare the answer with the reference claim by claim, in 2-4 sentences.")
    correct: Literal["yes", "no"] = Field(
        description="'yes' if nothing in the answer contradicts or misstates the reference, otherwise 'no'")
    complete: Literal["yes", "no"] = Field(
        description="'yes' if the answer covers the reference's main points, otherwise 'no'")


judge_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a strict evaluator comparing an AI system's answer with a reference answer.\n\n"
     "correct: answer 'no' if the answer states anything that contradicts the reference, attributes a "
     "number or claim to the wrong thing, or gets a key fact wrong. Extra details that do not contradict "
     "the reference are fine. Different wording is fine.\n"
     "complete: answer 'yes' only if the answer covers all the main points of the reference "
     "(for example, every number the reference gives)."),
    ("human", "Question: {question}\n\nReference answer: {reference}\n\nAnswer to evaluate: {answer}"),
])


def build_judge():
    llm = make_llm(config.JUDGE_MODEL)
    return (judge_prompt | llm.with_structured_output(Verdict, method="json_schema")).with_retry(stop_after_attempt=3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--rejudge", nargs="+", default=[],
                        help="question ids to judge again (e.g. after fixing their reference answers)")
    args = parser.parse_args()

    src = Path(args.results)
    out = src.with_suffix(".judged.jsonl")
    questions = {q["id"]: q for q in map(json.loads, open(EVAL_DIR / "questions.jsonl")) if q}
    rows = [json.loads(l) for l in open(src) if l.strip()]

    done = {}
    if out.exists():
        for line in open(out):
            r = json.loads(line)
            done[(r["id"], r["pipeline"])] = r

    judge = build_judge()
    with open(out, "w") as f:  # rewrite the file in input order, reusing finished verdicts
        for i, r in enumerate(rows, 1):
            key = (r["id"], r["pipeline"])
            if key in done and "judge" in done[key] and r["id"] not in args.rejudge:
                r = done[key]
            elif (r["category"] in JUDGED_CATEGORIES and not r.get("error") and not r.get("refused")):
                q = questions[r["id"]]
                print(f"[{i}/{len(rows)}] judging {r['pipeline']:<8} {r['id']}", flush=True)
                try:
                    v = judge.invoke({"question": q["question"], "reference": q["reference_answer"],
                                      "answer": r["answer"]})
                    r["judge"] = {"model": config.JUDGE_MODEL, "correct": v.correct,
                                  "complete": v.complete, "reasoning": v.reasoning}
                except Exception as e:
                    print(f"    judge failed: {type(e).__name__}: {e}", flush=True)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()

    print(f"\nJudged results: {out}\nReport: python -m evals.report {out}")


if __name__ == "__main__":
    main()
