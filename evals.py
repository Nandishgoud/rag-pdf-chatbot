"""Simple evaluation for the PDF chatbot.

Run from the project folder (with the venv active):
    python evals.py

It asks every question in eval_questions.json and checks:
  1. Answer check: for normal questions, the answer must contain every keyword.
     For "answerable": false questions, the bot must say it could not find the answer.
  2. Retrieval check (optional): if a question has "pages", at least one of those pages
     must be among the sources the bot used.
Results are saved to eval_results.csv.
"""
import csv
import json
import time

QUESTIONS_FILE = "eval_questions.json"
RESULTS_FILE = "eval_results.csv"
NOT_FOUND_TEXT = "could not find"
PAUSE_SECONDS = 6  # small pause between questions to stay under the free-tier limit


def check_answer(question, result):
    """Return True if the answer is correct for this question."""
    answer = result["answer"].lower()
    if not question.get("answerable", True):
        return NOT_FOUND_TEXT in answer
    return all(k.lower() in answer for k in question["keywords"])


def check_retrieval(question, result):
    """Return True/False if 'pages' is given, otherwise None."""
    pages = question.get("pages")
    if not pages:
        return None
    used = {s["page"] for s in result["sources"]}
    return bool(used & set(pages))


def percent(part, total):
    return round(100 * part / total, 1) if total else 0.0


def main():
    from rag import ask  # imported here so the checks above can be tested without an API key

    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)

    rows = []
    for i, q in enumerate(questions, start=1):
        try:
            result = ask(q["question"], q.get("source"))
        except Exception as e:
            result = {"answer": f"ERROR: {e}", "sources": []}

        correct = check_answer(q, result)
        retrieved = check_retrieval(q, result)
        rows.append({
            "no": i,
            "type": "answerable" if q.get("answerable", True) else "not in document",
            "question": q["question"],
            "correct": correct,
            "retrieval_hit": "" if retrieved is None else retrieved,
            "answer": result["answer"].replace("\n", " ")[:300],
        })
        print(f"{i}/{len(questions)}  {'PASS' if correct else 'FAIL'}  {q['question']}")
        time.sleep(PAUSE_SECONDS)

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    answerable = [r for r in rows if r["type"] == "answerable"]
    unanswerable = [r for r in rows if r["type"] != "answerable"]
    with_pages = [r for r in rows if r["retrieval_hit"] != ""]

    print("\n===== RESULTS =====")
    print(f"Questions: {len(rows)}")
    a = sum(r["correct"] for r in answerable)
    print(f"Answer accuracy (questions in the PDF): {a}/{len(answerable)} = {percent(a, len(answerable))}%")
    if unanswerable:
        u = sum(r["correct"] for r in unanswerable)
        print(f"Correctly said 'not found' (questions not in the PDF): {u}/{len(unanswerable)} = {percent(u, len(unanswerable))}%")
    if with_pages:
        h = sum(r["retrieval_hit"] for r in with_pages)
        print(f"Retrieval hit rate (right page found): {h}/{len(with_pages)} = {percent(h, len(with_pages))}%")
    overall = sum(r["correct"] for r in rows)
    print(f"Overall: {overall}/{len(rows)} = {percent(overall, len(rows))}%")
    print(f"Details saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()