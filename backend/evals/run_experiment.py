"""
מריץ ניסוי: שרשרת התרגום על כל הדוגמאות במאגר, ונותן ציון לכל אחת.
מריצים (מתיקיית backend), עם שם שמתאר את הגרסה:

    .venv\\Scripts\\python -m evals.run_experiment --name baseline

אחרי שמשפרים את ההנחיה, מריצים שוב עם שם אחר, ומשווים ב-LangSmith.
"""

import argparse

from langsmith import evaluate

from app import llm
from .create_dataset import DATASET_NAME
from .evaluators import canon, matched_correct, rule_correct


def target(inputs: dict) -> dict:
    """הפונקציה שנבדקת: הערה נכנסת, כלל (בצורה אחידה) יוצא."""
    # קוראים לשרשרת ישירות ולא ל-translate_note: שם יש נפילה שקטה למצב הדגמה,
    # והיא הייתה מסתירה תקלות במודל האמיתי.
    proposal = llm.chains()["translate"].invoke({"text": inputs["text"]})
    return canon(proposal.matched, proposal.kind, proposal.params)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="שם הניסוי, למשל baseline או improved")
    args = parser.parse_args()

    if not llm.USE_LLM:
        raise SystemExit("אין OPENAI_API_KEY ב-backend/.env, ובלי מודל אמיתי אין מה להעריך.")

    results = evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[matched_correct, rule_correct],
        experiment_prefix=args.name,
        metadata={"model": llm.MODEL},
        max_concurrency=4,
    )

    # סיכום קצר בטרמינל: אילו דוגמאות נכשלו
    total, failed = 0, []
    for row in results:
        total += 1
        scores = {r.key: r.score for r in row["evaluation_results"]["results"]}
        if scores.get("rule_correct") != 1:
            failed.append((row["example"].inputs["text"], row["run"].outputs))
    print(f"\nנכון לגמרי: {total - len(failed)} מתוך {total}")
    for text, out in failed:
        print(f"- {text}\n    המודל החזיר: {out}")


if __name__ == "__main__":
    main()
