"""
evaluate.py
Measure how good RETRIEVAL is: for each test question, does the search
find the chunk that contains the answer - and how high is it ranked?

Metrics:
  Hit@1  - share of questions where the correct chunk is ranked #1
  Hit@5  - ... is somewhere in the top 5 (what the LLM actually sees)
  Hit@10 - ... is somewhere in the top 10
  MRR    - Mean Reciprocal Rank: rank 1 = 1.0, rank 2 = 0.5, rank 5 = 0.2, not found = 0

Input:  data/eval/questions_draft.csv   (reviewed synthetic questions)
        data/eval/questions_manual.csv  (your hand-written questions)
Output: results/experiments.csv       (one line per run - your experiment log)
        results/<EXPERIMENT>_details.csv (one line per question)

Run from the project root:  python src/evaluate.py
"""

import csv
import statistics
from datetime import datetime
from pathlib import Path

from rag import retrieve

EXPERIMENT = "baseline"   # change this name every time you try something new
QUESTIONS_FILES = [
    Path("data/eval/questions_draft.csv"),
    Path("data/eval/questions_manual.csv"),
]
RESULTS_DIR = Path("results")
K = 10


def is_hit(chunk, q):
    """A retrieved chunk is correct if it is from the right file
    and its pages overlap the gold pages."""
    return (
        chunk["filename"] == q["gold_file"]
        and chunk["page_start"] <= int(q["gold_page_end"])
        and chunk["page_end"] >= int(q["gold_page_start"])
    )


def score(ranks):
    """Turn a list of ranks (None = not found) into the four metrics."""
    return {
        "hit@1": statistics.mean(r == 1 for r in ranks),
        "hit@5": statistics.mean(r is not None and r <= 5 for r in ranks),
        "hit@10": statistics.mean(r is not None for r in ranks),
        "mrr": statistics.mean(1 / r if r else 0 for r in ranks),
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    questions = []
    for path in QUESTIONS_FILES:
        if path.exists():
            with open(path, encoding="utf-8-sig") as f:
                questions += [q for q in csv.DictReader(f) if q["keep"].strip().lower() == "yes"]
    print(f"Evaluating {len(questions)} questions (experiment: {EXPERIMENT})\n")

    details = []
    for q in questions:
        chunks = retrieve(q["question"], top_k=K)
        rank = next((n for n, c in enumerate(chunks, start=1) if is_hit(c, q)), None)
        details.append({
            "question": q["question"],
            "origin": q["origin"],
            "rank": rank if rank else "NOT FOUND",
            "gold": f"{q['gold_file']} p{q['gold_page_start']}-{q['gold_page_end']}",
            "top1_found": f"{chunks[0]['filename']} p{chunks[0]['page_start']}-{chunks[0]['page_end']}",
        })
        print(f"   rank {str(rank) if rank else '-':>3}  |  {q['question'][:80]}")

    ranks = [d["rank"] if d["rank"] != "NOT FOUND" else None for d in details]

    # Overall scores + separate scores for synthetic vs manual questions
    print("\n" + "=" * 60)
    print(f"{'group':<12}{'n':>5}{'Hit@1':>9}{'Hit@5':>9}{'Hit@10':>9}{'MRR':>8}")
    groups = {"ALL": ranks}
    for origin in sorted({d["origin"] for d in details}):
        groups[origin] = [r for r, d in zip(ranks, details) if d["origin"] == origin]
    for name, group_ranks in groups.items():
        s = score(group_ranks)
        print(f"{name:<12}{len(group_ranks):>5}{s['hit@1']:>9.0%}{s['hit@5']:>9.0%}"
              f"{s['hit@10']:>9.0%}{s['mrr']:>8.2f}")
    print("=" * 60)

    # Save per-question details
    details_file = RESULTS_DIR / f"{EXPERIMENT}_details.csv"
    with open(details_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=details[0].keys())
        writer.writeheader()
        writer.writerows(details)

    # Append one line to the experiment log
    log_file = RESULTS_DIR / "experiments.csv"
    s = score(ranks)
    is_new = not log_file.exists()
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["date", "experiment", "n_questions", "hit@1", "hit@5", "hit@10", "mrr"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), EXPERIMENT, len(ranks),
                         f"{s['hit@1']:.3f}", f"{s['hit@5']:.3f}", f"{s['hit@10']:.3f}", f"{s['mrr']:.3f}"])

    print(f"\nDetails saved to {details_file}")
    print(f"Experiment logged in {log_file}")


if __name__ == "__main__":
    main()