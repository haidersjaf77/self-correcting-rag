"""Score a results file and print a comparison table (markdown, ready for the README).

    python -m evals.report evals/results/run-XXXX.jsonl

Metrics are all binary checks per question (no judge LLM), averaged per pipeline:
  behaviour   right action for the category and mode (answer from KB / answer from web / refuse)
  retrieval   for KB questions: at least one reference article was among the documents used
  citation    for KB questions: at least one cited document is a reference article
  key facts   share of the reference key facts that appear in the answer (case-insensitive)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

KB_CATEGORIES = {"in_corpus", "vague", "cross_topic"}
EVAL_DIR = Path(__file__).resolve().parent


def expected(category: str, pipeline: str) -> str:
    """The correct behaviour: 'kb' (answer from knowledge base), 'web' (answer from web) or 'refuse'."""
    if category in KB_CATEGORIES:
        return "kb"
    if category in ("out_of_scope", "recent"):
        return "web" if pipeline == "research" else "refuse"
    return "refuse"  # fabricated


def actual(r: dict) -> str:
    if r.get("error") or r["refused"]:
        return "refuse"
    return "kb" if r["answer_source"] == "knowledge_base" else "web"


def score(r: dict, q: dict) -> dict:
    s = {"behaviour": float(actual(r) == expected(r["category"], r["pipeline"]))}
    if r["category"] in KB_CATEGORIES and not r.get("error"):
        refs = set(q["reference_sources"])
        s["retrieval"] = float(bool(refs & set(r["sources"])))
        cited = r["cited"] or [int(n) for n in re.findall(r"[\[【](\d+)[\]】]", r["answer"]) if 1 <= int(n) <= len(r["sources"])]
        cited_urls = {r["sources"][i - 1] for i in cited}
        s["citation"] = float(bool(refs & cited_urls))
        if q["key_facts"]:
            ans = norm(r["answer"])
            s["key_facts"] = sum(norm(f) in ans for f in q["key_facts"]) / len(q["key_facts"])
    if r.get("judge"):
        s["correct"] = float(r["judge"]["correct"] == "yes")
        s["complete"] = float(r["judge"]["complete"] == "yes")
    if not r.get("error"):
        s["latency_s"] = r["latency_s"]
        s["llm_calls"] = r["llm_calls"]
        s["self_corrections"] = r["self_corrections"]
    return s


_NUMBER_WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}


def norm(text: str) -> str:
    """Compare facts ignoring formatting: '98.7 %' == '98.7%', '150 000' == '150,000',
    'multi‑agent' == 'multi-agent', 'fifteen' == '15', '49 percent' == '49%'."""
    text = text.lower()
    text = re.sub(r"\b(" + "|".join(_NUMBER_WORDS) + r")\b", lambda m: _NUMBER_WORDS[m.group(1)], text)
    text = re.sub(r"\s*percent\b", "%", text)
    return re.sub(r"[^a-z0-9%.]", "", text)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def fmt(v, metric):
    if v is None:
        return "–"
    if metric in ("latency_s",):
        return f"{v:.0f}s"
    if metric in ("llm_calls", "self_corrections"):
        return f"{v:.1f}"
    return f"{v:.0%}"


def main(path: str):
    questions = {q["id"]: q for q in map(json.loads, open(EVAL_DIR / "questions.jsonl")) if q}
    results = [json.loads(l) for l in open(path) if l.strip()]

    per_pipeline = defaultdict(lambda: defaultdict(list))
    per_category = defaultdict(lambda: defaultdict(list))
    failures = []
    errors = [r for r in results if r.get("error")]
    results = [r for r in results if not r.get("error")]   # a crash is not a refusal: don't score it
    for r in results:
        s = score(r, questions[r["id"]])
        for k, v in s.items():
            per_pipeline[r["pipeline"]][k].append(v)
        per_category[(r["category"], r["pipeline"])]["behaviour"].append(s["behaviour"])
        if not s["behaviour"]:
            failures.append(f"- `{r['pipeline']}` {r['id']}: expected **{expected(r['category'], r['pipeline'])}**, "
                            f"got **{actual(r)}**" + (f" (error: {r['error']})" if r.get("error") else ""))

    pipelines = [p for p in ("naive", "research", "scoped") if p in per_pipeline]
    metrics = ["behaviour", "retrieval", "citation", "key_facts", "self_corrections", "llm_calls", "latency_s"]
    if any(r.get("judge") for r in results):
        metrics[4:4] = ["correct", "complete"]   # judge metrics, only on judged (answered) runs

    print(f"## Overall ({len(results)} runs scored" + (f", {len(errors)} failed and excluded" if errors else "") + ")\n")
    print("| metric | " + " | ".join(pipelines) + " |")
    print("|---|" + "---|" * len(pipelines))
    for m in metrics:
        print(f"| {m} | " + " | ".join(fmt(mean(per_pipeline[p][m]), m) for p in pipelines) + " |")

    cats = ["in_corpus", "vague", "cross_topic", "out_of_scope", "recent", "fabricated"]
    print("\n## Correct behaviour by category\n")
    print("| category | " + " | ".join(pipelines) + " |")
    print("|---|" + "---|" * len(pipelines))
    for c in cats:
        if any((c, p) in per_category for p in pipelines):
            print(f"| {c} | " + " | ".join(fmt(mean(per_category[(c, p)]["behaviour"]), "b") for p in pipelines) + " |")

    wrong = [f"- `{r['pipeline']}` {r['id']}: {r['judge']['reasoning']}"
             for r in results if r.get("judge", {}).get("correct") == "no"]
    if wrong:
        print("\n## Judged incorrect (read these)\n")
        print("\n".join(wrong))

    if failures:
        print("\n## Wrong behaviour (read these)\n")
        print("\n".join(failures))

    if errors:
        print("\n## Failed runs (not scored; re-run the same command to retry them)\n")
        for r in errors:
            print(f"- `{r['pipeline']}` {r['id']}: {r['error'][:120]}")


if __name__ == "__main__":
    main(sys.argv[1])
