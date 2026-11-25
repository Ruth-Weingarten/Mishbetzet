"""
מריץ ניסוי: שרשרת התרגום על כל הדוגמאות במאגר, ונותן ציון לכל אחת.
מריצים (מתיקיית backend), עם שם שמתאר את הגרסה:

    .venv\\Scripts\\python -m evals.run_experiment --name baseline              (שרשרת התרגום הישנה: "לפני")
    .venv\\Scripts\\python -m evals.run_experiment --name agent --target agent   (הסוכן עם הכלים: "אחרי")

אחרי שמשפרים את ההנחיה, מריצים שוב עם שם אחר, ומשווים ב-LangSmith.
"""

import argparse

from langsmith import evaluate

from app import agent as agent_lib
from app import llm
from .create_dataset import DATASET_NAME
from .evaluators import canon, matched_correct, rule_correct


def target(inputs: dict) -> dict:
    """הפונקציה שנבדקת: הערה נכנסת, כלל (בצורה אחידה) יוצא."""
    # קוראים לשרשרת ישירות ולא ל-translate_note: שם יש נפילה שקטה למצב הדגמה,
    # והיא הייתה מסתירה תקלות במודל האמיתי.
    proposal = llm.chains()["translate"].invoke({"text": inputs["text"]})
    return canon(proposal.matched, proposal.kind, proposal.params)


def agent_target(inputs: dict) -> dict:
    """הסוכן החדש על אותה הערה: הכלל שהוא מציע (propose_rule) יוצא בצורה אחידה, כמו בשרשרת הישנה.
    אם הוא לא מציע כלל (עונה בטקסט, שואל, או מסרב), זה נחשב matched=False."""
    state = {"result": {"lessons": [], "violations": []}, "constraints": [], "chat": []}
    messages = agent_lib.start(inputs["text"], "", [])
    action = None
    for _ in range(agent_lib.MAX_STEPS):
        ai = agent_lib.call_model(messages)
        messages.append(ai)
        if not ai.tool_calls:
            break
        results, act, _ = agent_lib.run_tool_calls(ai, state)
        messages += results
        if act:
            action = act
            break
    if action and action["type"] == "add_rule":
        rule = action["rules"][0]
        return canon(True, rule["kind"], rule["params"])
    return canon(False, None, {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="שם הניסוי, למשל baseline או improved")
    parser.add_argument("--target", choices=["translate", "agent"], default="translate",
                        help="translate=שרשרת התרגום הישנה (לפני), agent=הסוכן עם הכלים (אחרי)")
    args = parser.parse_args()

    if not llm.USE_LLM:
        raise SystemExit("אין OPENAI_API_KEY ב-backend/.env, ובלי מודל אמיתי אין מה להעריך.")

    results = evaluate(
        agent_target if args.target == "agent" else target,
        data=DATASET_NAME,
        evaluators=[matched_correct, rule_correct],
        experiment_prefix=args.name,
        metadata={"model": llm.MODEL, "target": args.target},
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
