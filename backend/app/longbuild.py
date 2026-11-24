"""
בנייה ארוכה מחוץ לאתר: נותנים לפותר הרבה זמן (שעה, שלוש שעות), והמערכת הטובה ביותר שנמצאה
נשמרת כנקודת התחלה (seed_solution.json). אחר כך הבנייה באתר מתחילה ממנה ומשפרת אותה.

הרצה (מתיקיית backend):
    python -m app.longbuild 180        # 180 דקות
    python -m app.longbuild 60 --chunk 10

הפותר רץ בחתיכות של כמה דקות. בסוף כל חתיכה המערכת הטובה ביותר נשמרת, אז אפשר לעצור (Ctrl+C) בכל רגע.
"""
import argparse
import json
import time

from . import data as D
from . import solver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("minutes", type=float, help="כמה דקות לבנות")
    ap.add_argument("--chunk", type=float, default=10, help="אורך כל חתיכה בדקות (ברירת מחדל 10)")
    args = ap.parse_args()

    cons = [dict(r) for r in D.SCHOOL_RULES if r.get("enabled", True)]
    best_obj, best = None, solver._load_seed()
    start = time.time()
    n = 0
    try:
        while time.time() - start < args.minutes * 60:
            n += 1
            left = args.minutes * 60 - (time.time() - start)
            res = solver.solve(cons, time_limit=min(args.chunk * 60, left), hint=best or None)
            if res["status"] == "infeasible":
                print(f"חתיכה {n}: לא נמצאה מערכת, ממשיכה")
                continue
            obj = res["objective"]
            kinds = len(res["violations"])
            inst = sum(len(v["instances"]) for v in res["violations"])
            better = best_obj is None or obj < best_obj
            print(f"חתיכה {n}: ציון {obj:.0f} ({kinds} כללים לא קוימו, {inst} מקרים)"
                  f"{' - שופר ונשמר' if better else ' - לא שופר'}  [{(time.time() - start) / 60:.0f} דקות]", flush=True)
            if better:
                best_obj, best = obj, res["lessons"]
                with open(solver._SEED, "w", encoding="utf-8") as f:
                    json.dump(best, f, ensure_ascii=False)
    except KeyboardInterrupt:
        print("נעצר. המערכת הטובה ביותר כבר נשמרה.")


if __name__ == "__main__":
    main()
