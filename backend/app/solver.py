"""
פותר האילוצים (CP-SAT של Google OR-Tools).

זה לא חומר הלימוד של הקורס, אבל כדאי להבין את הרעיון:
- לכל (כיתה, מקצוע, יום, שעה) יש משתנה כן/לא: האם המקצוע מתקיים שם.
- אילוצי חובה: הפותר חייב לקיים אותם (אין מורה בשתי כיתות באותה שעה וכו').
- אילוצים רכים (כללים ובקשות): לכל מופע יש משתנה "הופר". הפותר מנסה
  למזער את מספר ההפרות, ומחזיר לנו בדיוק אילו הופרו.

כל אילוץ רך מתואר כמילון (dict):
    {"id": "R1", "kind": "...", "params": {...}, "text": "...",
     "hard": False, "waived": ["מפתח-מופע", ...]}
- hard=True  -> המנהלת החליטה לאכוף. הופך לחובה.
- waived     -> מופעים שהמנהלת הסכימה לוותר עליהם.
"""

import os

from ortools.sat.python import cp_model

from . import data as D

DEFAULT_WEIGHTS = {
    "avoid_prev_homeroom": 2,
}
WEIGHT = 10
GAP_WEIGHT = 6   # קנס לכל חלון של מורה, בנוסף לכללים


def _period_label(d, p):
    return f"{D.DAYS[d]} שעה {p + 1}"


def solve(constraints, pins=None, time_limit=8.0, previous=None):
    """previous: השיעורים מהפתרון הקודם. הפותר משתדל לא להזיז אותם (יציבות)."""
    pins = pins or []
    m = cp_model.CpModel()
    slots = [(d, p) for d in range(6) for p in range(D.PERIODS_PER_DAY[d])]

    # y[c, s, d, p] = האם מקצוע s של כיתה c מתקיים ביום d בשעה p
    y = {}
    for c in D.CLASSES:
        for s in D.CLASS_CURRICULUM[c]:
            for (d, p) in slots:
                y[c, s, d, p] = m.NewBoolVar(f"y_{c}_{s}_{d}_{p}")

    def is_pullout(c, s):
        return D.ASSIGNMENT[(c, s)]["pullout"]

    # occ[c, d, p] = האם לכיתה יש שיעור במשבצת (שיעורי סיוע לא נספרים: הם במקביל לשיעור אחר)
    occ = {}
    for c in D.CLASSES:
        regular = [s for s in D.CLASS_CURRICULUM[c] if not is_pullout(c, s)]
        for (d, p) in slots:
            o = m.NewBoolVar("")
            m.Add(sum(y[c, s, d, p] for s in regular) == o)     # לכל היותר שיעור אחד
            occ[c, d, p] = o
        for d in range(6):
            P = D.PERIODS_PER_DAY[d]
            # --- חובה: הכיתה לומדת בכל יום, מהשעה הראשונה ובלי חלונות לתלמידות
            m.Add(occ[c, d, 0] == 1)
            for p in range(P - 1):
                m.Add(occ[c, d, p + 1] <= occ[c, d, p])
        # --- שיעור סיוע מתקיים רק בזמן שהכיתה בבית הספר
        for s in D.CLASS_CURRICULUM[c]:
            if is_pullout(c, s):
                for (d, p) in slots:
                    m.Add(y[c, s, d, p] <= occ[c, d, p])

    # --- חובה: המכוון מתקיים במלואו
    for c in D.CLASSES:
        for s, h in D.CLASS_CURRICULUM[c].items():
            m.Add(sum(y[c, s, d, p] for (d, p) in slots) == h)

    # --- חובה: הקבצה = כל הכיתות בקבוצה לומדות את המקצוע באותה שעה
    for b in D.BLOCKS.values():
        first = b["classes"][0]
        for c in b["classes"][1:]:
            for (d, p) in slots:
                m.Add(y[c, b["subject"], d, p] == y[first, b["subject"], d, p])

    # --- מאגר: בחירת מורה אחת מתוך המאגר
    choice = {}
    for (c, s), info in D.ASSIGNMENT.items():
        if info["kind"] == "pool":
            options = [t for t in info["teachers"] if c not in D.blocked().get(t, [])]
            for t in options:
                choice[c, s, t] = m.NewBoolVar(f"ch_{c}_{s}_{t}")
            m.AddExactlyOne(choice[c, s, t] for t in options)

    # תרומה של כל מורה לכל משבצת. בהקבצה המורה נספרת פעם אחת (לפי הכיתה הראשונה).
    contrib = {t: {sl: [] for sl in slots} for t in D.TEACHERS}
    for (c, s), info in D.ASSIGNMENT.items():
        if info["block"] and D.BLOCKS[info["block"]]["classes"][0] != c:
            continue
        for (d, p) in slots:
            if info["kind"] == "pool":
                for t in info["teachers"]:
                    if (c, s, t) not in choice:
                        continue
                    w = m.NewBoolVar("")
                    m.AddBoolAnd([y[c, s, d, p], choice[c, s, t]]).OnlyEnforceIf(w)
                    m.AddBoolOr([y[c, s, d, p].Not(), choice[c, s, t].Not()]).OnlyEnforceIf(w.Not())
                    contrib[t][(d, p)].append(w)
            else:
                for t in info["teachers"]:
                    contrib[t][(d, p)].append(y[c, s, d, p])

    # --- חובה: מורה לא נמצאת בשני מקומות באותה שעה
    busy = {}
    for t in D.TEACHERS:
        for (d, p) in slots:
            b = m.NewBoolVar("")
            m.Add(sum(contrib[t][(d, p)]) == b)
            busy[t, d, p] = b

    # --- חובה: חדר מיוחד לא תפוס יותר מהקיבולת שלו
    for room, cap in D.ROOM_CAPACITY.items():
        uses = [(c, s) for (c, s) in D.ASSIGNMENT if D.ROOMS.get(s) == room]
        for (d, p) in slots:
            m.Add(sum(D.ASSIGNMENT[(c, s)]["rooms"] * y[c, s, d, p] for (c, s) in uses) <= cap)

    # --- נעיצות מהצ'אט ("תעבירי את החשבון של ג'2 לרביעי שעה 3")
    for pin in pins:
        m.Add(y[pin["cls"], pin["subject"], pin["day"], pin["period"]] == 1)

    # --- אילוצים רכים
    penalties = []      # (משתנה הפרה, משקל)
    instances = []      # (מזהה אילוץ, מפתח מופע, תווית, משתנה הפרה)

    def soft(cons, key, label, viol, weight=None):
        """רושם מופע של אילוץ רך. אם נאכף: ההפרה אסורה. אם ויתרו: לא נספר."""
        if cons.get("hard") or key in cons.get("hard_keys", []):
            # hard: כל הכלל נאכף. hard_keys: רק המופעים האלה אסור להפר.
            m.Add(viol == 0)
        elif key in cons.get("waived", []):
            return
        else:
            penalties.append((viol, weight or DEFAULT_WEIGHTS.get(cons["kind"], WEIGHT)))
        instances.append((cons["id"], key, label, viol))

    gap_cache = {}

    def day_gaps(t, d):
        """משתני "חלון" של מורה ביום: שעה פנויה שיש לפניה וגם אחריה שיעור.
        נבנים פעם אחת ונשמרים, כי כמה כללים משתמשים בהם."""
        if (t, d) not in gap_cache:
            P = D.PERIODS_PER_DAY[d]
            gaps = []
            for p in range(1, P - 1):
                before = m.NewBoolVar("")
                after = m.NewBoolVar("")
                m.AddMaxEquality(before, [busy[t, d, q] for q in range(p)])
                m.AddMaxEquality(after, [busy[t, d, q] for q in range(p + 1, P)])
                g = m.NewBoolVar("")
                m.Add(g <= before)
                m.Add(g <= after)
                m.Add(g <= 1 - busy[t, d, p])
                m.Add(g >= before + after - busy[t, d, p] - 1)
                gaps.append(g)
            gap_cache[t, d] = gaps
        return gap_cache[t, d]

    for cons in constraints:
        k, prm = cons["kind"], cons.get("params", {})

        if k == "class_daily_load":
            # חובה: יום לימודים סביר לכל כיתה (ראשון עד חמישי): מספר שיעורים קרוב לממוצע,
            # ולא 7 שיעורים ביום אחד ושיעור אחד ביום אחר. שישי קצר ולא נכלל.
            spread_by = prm.get("tolerance", 1)
            for c in D.CLASSES:
                total = sum(h for s, h in D.CLASS_CURRICULUM[c].items() if not is_pullout(c, s))
                avg = (total - D.PERIODS_PER_DAY[5]) / 5
                lo = min(prm.get("min_lessons", 5), int(avg))   # אין כיתה עם פחות מ-5 שיעורים ביום (ראשון-חמישי)
                for d in range(5):
                    hi = min(D.PERIODS_PER_DAY[d], -(-int(avg * 10) // 10) + spread_by)
                    day_total = sum(occ[c, d, p] for p in range(D.PERIODS_PER_DAY[d]))
                    m.Add(day_total >= lo)
                    m.Add(day_total <= hi)
                if prm.get("friday_full"):
                    # שישי: כל ארבע השעות, כמו במערכת של בית הספר
                    for p in range(D.PERIODS_PER_DAY[5]):
                        m.Add(occ[c, 5, p] == 1)

        elif k == "teacher_free_day_base":
            # חובה: לכל מורה לפחות יום חופשי אחד בשבוע (אין מורה שעובדת 6 ימים)
            for t in D.TEACHERS:
                works = []
                for d in range(6):
                    w = m.NewBoolVar("")
                    m.AddMaxEquality(w, [busy[t, d, p] for p in range(D.PERIODS_PER_DAY[d])])
                    works.append(w)
                m.Add(sum(works) <= 6 - prm.get("min_free_days", 1))

        elif k == "teacher_max_wait":
            # חובה: מורה לא ממתינה יותר מ-max_wait שעות רצופות בין שני שיעורים באותו יום
            mx = prm.get("max_wait", 1)
            for t in D.TEACHERS:
                for d in range(6):
                    P = D.PERIODS_PER_DAY[d]
                    for q in range(P):
                        for r in range(q + mx + 2, P):
                            m.AddBoolOr([busy[t, d, q].Not(), busy[t, d, r].Not()]
                                        + [busy[t, d, x] for x in range(q + 1, r)])

        elif k == "first_period_kodesh":
            for c in D.CLASSES:
                kod = [s for s in D.CLASS_CURRICULUM[c] if D.SUBJECTS[s] == "kodesh" and not is_pullout(c, s)]
                if "min_days" in prm:
                    # במערכת האמיתית: קודש בשעה הראשונה ברוב הימים, לא בכולם.
                    # הכלל: לפחות min_days ימים בכל כיתה. כל יום חסר מעבר לכך הוא הפרה.
                    miss = []
                    for d in range(6):
                        got = m.NewBoolVar("")
                        m.Add(sum(y[c, s, d, 0] for s in kod) >= got)
                        miss.append(1 - got)
                    allowed = 6 - prm["min_days"]
                    extra = m.NewIntVar(0, 6, "")
                    m.Add(extra >= sum(miss) - allowed)
                    soft(cons, c, f"{c} · קודש בשעה הראשונה בפחות מ־{prm['min_days']} ימים", extra)
                    continue
                for d in range(6):
                    v = m.NewBoolVar("")
                    m.Add(sum(y[c, s, d, 0] for s in kod) + v >= 1)
                    soft(cons, f"{c}|{d}", f"{c} · {D.DAYS[d]}", v)

        elif k == "subject_days":
            s, allowed = prm["subject"], set(prm["days"])
            for c in D.CLASSES:
                if s not in D.CLASS_CURRICULUM[c]:
                    continue
                v = m.NewBoolVar("")
                bad = [y[c, s, d, p] for (d, p) in slots if d not in allowed]
                m.Add(sum(bad) <= len(bad) * v)
                soft(cons, c, c, v)

        elif k == "no_double":
            s = prm["subject"]
            for c in D.CLASSES:
                if s not in D.CLASS_CURRICULUM[c] or ("grades" in prm and D.grade_of(c) not in prm["grades"]):
                    continue
                for d in range(6):
                    v = m.NewBoolVar("")
                    for p in range(D.PERIODS_PER_DAY[d] - 1):
                        m.Add(y[c, s, d, p] + y[c, s, d, p + 1] <= 1 + v)
                    soft(cons, f"{c}|{d}", f"{c} · {D.DAYS[d]}", v)

        elif k == "spread":
            s = prm["subject"]
            for c in D.CLASSES:
                if s not in D.CLASS_CURRICULUM[c]:
                    continue
                for d in range(6):
                    v = m.NewBoolVar("")
                    m.Add(sum(y[c, s, d, p] for p in range(D.PERIODS_PER_DAY[d])) <= 1 + 6 * v)
                    soft(cons, f"{c}|{d}", f"{c} · {D.DAYS[d]}", v)

        elif k == "teacher_gaps":
            mx = prm.get("max_per_day", 1)
            for t in D.TEACHERS:
                for d in prm.get("days", range(6)):
                    v = m.NewBoolVar("")
                    m.Add(sum(day_gaps(t, d)) <= mx + D.PERIODS_PER_DAY[d] * v)
                    soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

        elif k == "max_gaps_per_week":
            # סך החלונות של המורה בכל השבוע
            # הקנס עולה עם כל חלון מעל המותר (לא רק "עברה / לא עברה")
            mx = prm.get("max", 2)
            for t in D.TEACHERS:
                week = [g for d in range(6) for g in day_gaps(t, d)]
                v = m.NewIntVar(0, len(week), "")
                m.Add(v >= sum(week) - mx)
                soft(cons, t, t, v)

        elif k == "min_lessons_per_day":
            # אם המורה מגיעה ביום מסוים, שתלמד בו לפחות mn שיעורים
            mn = prm.get("min", 2)
            for t in D.TEACHERS:
                for d in range(6):
                    P = D.PERIODS_PER_DAY[d]
                    day_busy = [busy[t, d, p] for p in range(P)]
                    works = m.NewBoolVar("")
                    m.AddMaxEquality(works, day_busy)
                    v = m.NewBoolVar("")
                    m.Add(sum(day_busy) + mn * v >= mn * works)
                    soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

        elif k == "short_day_early":
            # יום קצר (עד max_lessons שיעורים): השיעורים צמודים, ומסתיימים עד last_period
            mx, last = prm.get("max_lessons", 2), prm.get("last_period", 2)
            for t in D.TEACHERS:
                for d in range(6):
                    P = D.PERIODS_PER_DAY[d]
                    day_busy = [busy[t, d, p] for p in range(P)]
                    works = m.NewBoolVar("")
                    m.AddMaxEquality(works, day_busy)
                    short = m.NewBoolVar("")
                    # אם המורה מגיעה ולא מסומן "יום קצר", חייבים להיות לה יותר מ-mx שיעורים
                    m.Add(sum(day_busy) >= (mx + 1) * (works - short))
                    v = m.NewBoolVar("")
                    for p in range(last + 1, P):
                        m.Add(busy[t, d, p] <= v + 1 - short)
                    for g in day_gaps(t, d):
                        m.Add(g <= v + 1 - short)
                    soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

        elif k == "max_work_days":
            # מורה עם יותר מ-threshold שעות: עד above ימים. אחרות: עד below ימים.
            hours = D.teacher_hours()
            for t in D.TEACHERS:
                limit = prm.get("above", 5) if hours[t] > prm.get("threshold", 20) else prm.get("below", 4)
                works = []
                for d in range(6):
                    w = m.NewBoolVar("")
                    m.AddMaxEquality(w, [busy[t, d, p] for p in range(D.PERIODS_PER_DAY[d])])
                    works.append(w)
                v = m.NewBoolVar("")
                m.Add(sum(works) <= limit + 6 * v)
                soft(cons, t, t, v)

        elif k == "free_day":
            t, d = prm["teacher"], prm["day"]
            v = m.NewBoolVar("")
            for p in range(D.PERIODS_PER_DAY[d]):
                m.Add(busy[t, d, p] <= v)
            soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

        elif k == "teacher_not_periods":
            for t in prm["teachers"]:
                for d in prm.get("days", range(6)):
                    v = m.NewBoolVar("")
                    for p in prm["periods"]:
                        if p < D.PERIODS_PER_DAY[d]:
                            m.Add(busy[t, d, p] <= v)
                    soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

        elif k == "teacher_end_by":
            t, d, last = prm["teacher"], prm["day"], prm["last_period"]
            v = m.NewBoolVar("")
            for p in range(last + 1, D.PERIODS_PER_DAY[d]):
                m.Add(busy[t, d, p] <= v)
            soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

        elif k == "teacher_start_from":
            t, d, first = prm["teacher"], prm["day"], prm["first_period"]
            v = m.NewBoolVar("")
            for p in range(0, min(first, D.PERIODS_PER_DAY[d])):
                m.Add(busy[t, d, p] <= v)
            soft(cons, f"{t}|{d}", f"{t} · {D.DAYS[d]}", v)

    # מובנה: עדיף שמורה לא תקבל מהמאגר כיתה שחינכה בשנה שעברה
    # --- מינימום חלונות כללי: כל חלון של מורה (בכל יום) עולה קנס קטן.
    # המערכת האמיתית הגיעה בממוצע לפחות מחלון אחד בשבוע למורה, ומורות התלוננו גם על זה.
    for t in D.TEACHERS:
        for d in range(6):
            for g in day_gaps(t, d):
                penalties.append((g, GAP_WEIGHT))

    prev_cons = {"id": "POOL", "kind": "avoid_prev_homeroom",
                 "text": "במאגר: עדיף לא לכיתה שהמורה חינכה בשנה שעברה"}
    for (c, s, t), var in choice.items():
        if D.PREV_HOMEROOM.get(t) == c:
            soft(prev_cons, f"{t}|{c}", f"{t} · {c}", var)

    # יציבות: כל שיעור שזז ממקומו בפתרון הקודם עולה נקודה אחת.
    # כך החלטה קטנה של המנהלת לא "מערבבת" את כל המערכת.
    stability = []
    for l in previous or []:
        var = y.get((l["cls"], l["subject"], l["day"], l["period"]))
        if var is not None:
            m.AddHint(var, 1)
            stability.append(1 - var)

    m.Minimize(sum(w * v for v, w in penalties) + sum(stability))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = min(16, os.cpu_count() or 8)
    status = solver.Solve(m)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "lessons": [], "violations": []}

    lessons = []
    for c in D.CLASSES:
        for s in D.CLASS_CURRICULUM[c]:
            info = D.ASSIGNMENT[(c, s)]
            if info["kind"] == "pool":
                teachers = [t for t in info["teachers"] if (c, s, t) in choice and solver.Value(choice[c, s, t])]
            else:
                teachers = info["teachers"]
            for (d, p) in slots:
                if solver.Value(y[c, s, d, p]):
                    lessons.append({"cls": c, "subject": s, "teachers": teachers,
                                    "day": d, "period": p, "room": D.ROOMS.get(s),
                                    "group": D.SUBJECTS[s], "pullout": info["pullout"]})

    by_id = {}
    for cid, key, label, var in instances:
        if solver.Value(var):
            by_id.setdefault(cid, []).append({"key": key, "label": label})
    cons_by_id = {c["id"]: c for c in constraints}
    cons_by_id["POOL"] = prev_cons
    violations = [
        {"id": cid, "text": cons_by_id[cid]["text"], "kind": cons_by_id[cid]["kind"],
         "instances": inst}
        for cid, inst in by_id.items()
    ]
    return {
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "lessons": lessons,
        "violations": violations,
        "objective": solver.ObjectiveValue(),
    }


def diff_lessons(old, new):
    """כמה שיעורים זזו בין שני פתרונות."""
    key = lambda l: (l["cls"], l["subject"], l["day"], l["period"])
    a, b = {key(l) for l in old}, {key(l) for l in new}
    return len(a - b)


def diff_violations(old, new):
    """אילו הפרות נוספו בפתרון החדש לעומת הקודם."""
    old_keys = {(v["id"], i["key"]) for v in old for i in v["instances"]}
    added = []
    for v in new:
        inst = [i for i in v["instances"] if (v["id"], i["key"]) not in old_keys]
        if inst:
            added.append({**v, "instances": inst})
    return added


def alternatives(constraints, pins, cid, previous, current_violations, k=3, time_limit=4):
    """
    מוצא עד k דרכים שונות לאכוף את הכלל cid. כל דרך עולה מחיר אחר.
    הרעיון: מוצאים את הדרך הזולה ביותר, ואז "אוסרים" את המחיר שלה
    (הופכים את המופעים שנפגעו לחובה), ומבקשים מהפותר דרך אחרת.
    """
    found = []
    forbid = {}          # {מזהה כלל: [מפתחות מופעים שאסור להפר]}
    for _ in range(k):
        trial = []
        for c in constraints:
            c = dict(c)
            if c["id"] == cid:
                c["hard"] = True
            if c["id"] in forbid:
                c["hard_keys"] = list(c.get("hard_keys", [])) + forbid[c["id"]]
            trial.append(c)
        sim = solve(trial, pins, time_limit=time_limit, previous=previous)
        if sim["status"] == "infeasible":
            break
        added = diff_violations(current_violations, sim["violations"])
        found.append({"added": added, "forbid": {k2: list(v) for k2, v in forbid.items()}})
        blockable = [a for a in added if a["id"] != "POOL"]
        if not blockable:
            break        # אין מחיר (או רק מחיר שאי אפשר לאסור): אין טעם לחפש עוד
        for a in blockable:
            forbid.setdefault(a["id"], []).extend(i["key"] for i in a["instances"])
    return found
