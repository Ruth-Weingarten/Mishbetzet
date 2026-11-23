"""
הגרף של בניית מערכת השעות. זה חומר הלימוד המרכזי של הפרויקט.

המבנה בקצרה:

  START
    -> load_data            טוען כללים ובקשות
    -> translate_notes      מודל השפה מתרגם הערות חופשיות לכללים
    -> review_translations  ⏸ עצירה: המנהלת מאשרת את התרגומים
    -> solve                פותר האילוצים בונה מערכת
    -> [ענף מותנה]
         בלתי אפשרי -> diagnose
         יש חריגות   -> explain  (הסבר + אפשרויות)
         אין חריגות  -> await_principal
    -> await_principal      ⏸ עצירה: מחכה להודעה של המנהלת
    -> [ענף מותנה לפי סוג ההודעה]
         כפתור   -> apply_decision -> solve      (לולאה!)
         "להראות דרכים" -> alternatives -> await_principal   (מחשב עד 3 דרכים לאכוף)
         טקסט    -> interpret -> [ענף]
                      לא ברור  -> clarify ⏸ -> interpret
                      שאלה     -> answer -> await_principal
                      פעולה    -> simulate -> confirm ⏸ -> apply_action -> solve (לולאה!)
         אישור   -> finalize -> await_principal
"""

import operator
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import data as D
from . import llm, solver

MAX_ALTERNATIVES = 3     # כמה דרכים שונות לאכוף להציע למנהלת
BUILD_TIME_LIMIT = 300   # שניות לכל היותר לבניית מערכת (49 כיתות: כמה דקות). עוצר מוקדם אם מצא את הטובה ביותר
TRIAL_TIME_LIMIT = 30    # שניות לכל היותר לכל ניסיון: הדמיה של בקשה, או דרך לאכוף


# =====================================================================
# 1. המצב (State): כל מה שעובר בין הצמתים
# =====================================================================

class TimetableState(TypedDict, total=False):
    constraints: list[dict]          # כל הכללים והבקשות הפעילים
    pins: list[dict]                 # שיעורים שהמנהלת נעצה במקום
    proposals: list[dict]            # תרגומים שממתינים לאישור
    result: dict                     # הפתרון האחרון של הפותר
    conflicts: list[dict]            # החריגות, עם אפשרויות, למנהלת
    chat: Annotated[list[dict], operator.add]   # יומן ההתכתבות (מצטבר!)
    incoming: Optional[dict]         # ההודעה האחרונה מהמנהלת
    action: Optional[dict]           # פעולה שמודל השפה הבין מהטקסט
    simulation: Optional[dict]       # תוצאת ההדמיה של הפעולה
    round: int                       # מונה סבבים
    published: bool


def llm_notice():
    """הודעה למנהלת אם הקריאה האחרונה למודל נכשלה (ועברנו למצב פשוט)."""
    return say(llm.LLM_DOWN_MSG) if llm.take_failure() else []


def say(text, **extra):
    """הודעה של המערכת ביומן."""
    return [{"role": "system", "text": text, **extra}]


# =====================================================================
# 2. הצמתים (Nodes): כל צומת = פונקציה שמקבלת מצב ומחזירה עדכון
# =====================================================================

def load_data(state: TimetableState):
    constraints = [dict(r, source="rule") for r in D.SCHOOL_RULES if r.get("enabled", True)]
    unconfirmed = []
    for t, f in D.FORMS.items():
        if f.get("free_day"):
            constraints.append({
                "id": f"F-{t}", "kind": "free_day", "source": "form",
                "params": {"teacher": t, "day": D.DAYS.index(f["free_day"])},
                "alt_day": D.DAYS.index(f["alt_day"]) if f.get("alt_day") else None,
                "text": f"{t}: יום {f['free_day']} חופשי",
            })
        # בקשה חופשית שהמורה אישרה את התרגום שלה: נכנסת ישר לבנייה.
        # זה עניין בין המורה למערכת, והמנהלת לא צריכה לאשר אותו שוב.
        rule = f.get("confirmed_rule")
        if f.get("free_text") and rule and rule.get("matched"):
            constraints.append({"id": f"T-{t}", "kind": rule["kind"], "params": rule["params"],
                                "text": rule["summary"], "source": "form", "original": f["free_text"]})
        elif f.get("free_text"):
            unconfirmed.append(f"{t}: \"{f['free_text']}\"")
    msg = (f"טענתי את נתוני בית הספר: {len(D.CLASSES)} כיתות, {len(D.TEACHERS)} מורות, "
           f"{len(D.FORMS)} טפסים ו־{len(D.SCHOOL_RULES)} כללים.")
    # אזהרה: מורה ששובצה קבוע בכיתה שסימנה בטופס שאינה יכולה ללמד
    clashes = [f"{t} ב{c}" for t, cs in D.blocked().items() for c in cs
               for (cc, s), info in D.ASSIGNMENT.items()
               if cc == c and info["kind"] != "pool" and t in info["teachers"]]
    if clashes:
        msg += " שימי לב: בטבלת השיבוץ יש מורה בכיתה שביקשה לא ללמד: " + ", ".join(sorted(set(clashes)))
    if unconfirmed:
        msg += (" בקשה אחת של מורה לא תורגמה לכלל." if len(unconfirmed) == 1
                else f" {len(unconfirmed)} בקשות של מורות לא תורגמו לכלל.")
    chat = say(msg)
    if unconfirmed:
        chat += say("את הבקשות האלה של מורות לא הצלחתי לתרגם לכלל: " + "\n" + "\n".join("• " + u for u in unconfirmed) + ". "
                    "אם תרצי שאתחשב בהן, כתבי לי כאן במילים שלך מה צריך, ואנסה שוב.")
    return {"constraints": constraints, "pins": [], "round": 0, "published": False, "chat": chat}


def translate_notes(state: TimetableState):
    """מתרגם רק את ההערות של המנהלת. בקשות המורות כבר אושרו על ידי המורות עצמן."""
    proposals = []
    for n in D.PRINCIPAL_NOTES:
        p = llm.translate_note(n["text"])
        proposals.append({"id": n["id"], "source": "מנהלת", "original": n["text"], **p.model_dump()})
    return {"proposals": proposals, "chat": llm_notice()}


def review_translations(state: TimetableState):
    # ⏸ עצירה לאישור אדם #1: הגרף נעצר כאן עד שהמנהלת עונה.
    answer = interrupt({"type": "review", "items": state["proposals"]})
    approved = set(answer.get("approved", []))

    new_constraints = list(state["constraints"])
    notes = []
    for p in state["proposals"]:
        if p["matched"] and p["id"] in approved:
            new_constraints.append({"id": p["id"], "kind": p["kind"], "params": p["params"],
                                    "text": p["summary"], "source": "note", "original": p["original"]})
        elif not p["matched"]:
            notes.append(p["original"])
    msg = f"אושרו {len([p for p in state['proposals'] if p['id'] in approved and p['matched']])} כללים מההערות."
    if notes:
        msg += (" הערה אחת שלא הצלחתי לתרגם לכלל נשמרה כהערה." if len(notes) == 1
                else f" {len(notes)} הערות שלא הצלחתי לתרגם לכלל נשמרו כהערות.")
    chat = say(msg)
    if notes:
        # לא "לא הבנתי" וזהו: מזמינים את המנהלת להסביר במילים שלה, באותו צ'אט.
        # ההסבר שלה יעבור את המסלול הרגיל: interpret, ואם צריך clarify, simulate ו-confirm.
        quoted = "\n" + "\n".join(f"• \"{n}\"" for n in notes)
        chat += say(f"את ההערות האלה לא הצלחתי לתרגם לכלל: {quoted}. "
                    "אם תרצי, כתבי לי כאן במילים שלך מה התכוונת, ואנסה שוב. אפשר גם להתעלם.")
    return {"constraints": new_constraints, "chat": chat}


def solve(state: TimetableState):
    prev = (state.get("result") or {}).get("lessons")
    result = solver.solve(state["constraints"], state.get("pins", []),
                          time_limit=BUILD_TIME_LIMIT, previous=prev)
    rnd = state.get("round", 0) + 1
    if result["status"] == "infeasible":
        return {"result": result, "round": rnd}
    n = len(result["violations"])
    text = (f"סבב {rnd}: המערכת נבנתה. {len(result['lessons'])} שיעורים שובצו, "
            f"אין התנגשויות, והמכוון מתקיים במלואו. ")
    text += f"{n} כללים או בקשות לא קוימו במלואם." if n else "כל הכללים והבקשות קוימו."
    if result["status"] == "feasible":
        text += " (נגמר הזמן לפני שבדקתי את כל האפשרויות, אז ייתכן שאפשר עוד לשפר.)"
    return {"result": result, "round": rnd, "chat": say(text)}


def diagnose(state: TimetableState):
    """אי אפשר לבנות בכלל. מחפשים סיבה שהמנהלת יכולה לתקן, ומסבירים אותה בשפה שלה."""
    problems = D.data_problems()
    if problems:
        text = ("לא הצלחתי לבנות מערכת, ומצאתי את הסיבה: " + " ".join(problems)
                + " אחרי התיקון אפשר לבנות שוב.")
    else:
        text = ("לא הצלחתי לבנות מערכת שמקיימת את כל מה שקבעת כחובה. "
                "כדאי לבדוק בלשונית \"שיבוץ\" שלאף מורה לא שובצו יותר שעות ממה שיש בשבוע.")
    return {"conflicts": [], "chat": say(text)}


def explain(state: TimetableState):
    """לכל חריגה: הסבר ואפשרויות. את הדרכים לאכוף מחשב הצומת alternatives, רק כשמבקשים."""
    result = state["result"]
    by_id = {c["id"]: c for c in state["constraints"]}
    conflicts = []
    for v in result["violations"]:
        cons = by_id.get(v["id"], {})
        options = [{"id": "waive", "label": "לוותר במקומות האלה"}]
        if v["id"] != "POOL":
            # את הדרכים לאכוף מחשבים רק כשהמנהלת מבקשת (צומת alternatives)
            options.append({"id": "show_alternatives", "label": "לאכוף: להראות לי דרכים אפשריות"})
        if cons.get("kind") == "free_day" and cons.get("alt_day") is not None:
            options.append({"id": "alt_day", "label": f"לתת את היום החלופי: {D.DAYS[cons['alt_day']]}"})
        conflicts.append({**v, "explanation": llm.explain(v), "options": options})
    return {"conflicts": conflicts, "chat": llm_notice()}


def alternatives(state: TimetableState):
    """המנהלת ביקשה לאכוף: מחשבים עד שלוש דרכים, כל אחת עם המחיר שלה, ומעדכנים את הפתק."""
    # הבקשה הגיעה מכפתור, או מהצ'אט ("תאכפי את...")
    cid = state["incoming"].get("conflict_id") or (state.get("action") or {}).get("conflict_id")
    result = state["result"]
    alts = solver.alternatives(state["constraints"], state.get("pins", []), cid,
                               previous=result["lessons"], current_violations=result["violations"],
                               k=MAX_ALTERNATIVES, time_limit=TRIAL_TIME_LIMIT)
    letters = "אבג"
    new_options = []
    for i, a in enumerate(alts):
        if a["added"]:
            cost = "; ".join(f"{x['text']} ({', '.join(j['label'] for j in x['instances'][:3])})"
                             for x in a["added"])
            impact = "במחיר: " + cost
        else:
            impact = "בלי לפגוע בשום כלל או בקשה"
        new_options.append({"id": f"alt:{i}", "label": f"דרך {letters[i]}'", "impact": impact,
                            "forbid": a["forbid"]})
    if not new_options:
        new_options = [{"id": "impossible", "label": "אי אפשר לאכוף",
                        "impact": "זה ישבור אילוץ חובה", "disabled": True}]

    conflicts = []
    for c in state["conflicts"]:
        if c["id"] == cid:
            opts = [o for o in c["options"] if o["id"] != "show_alternatives"]
            c = {**c, "options": opts + new_options}
        conflicts.append(c)
    n = len([o for o in new_options if not o.get("disabled")])
    return {"conflicts": conflicts,
            "chat": say((f"מצאתי {n} דרכים לאכוף את \"{next(c['text'] for c in conflicts if c['id'] == cid)}\". "
                         "כל דרך עולה מחיר אחר. בחרי אחת מהן בפתק.") if n > 1 else
                        (f"מצאתי דרך אחת לאכוף את \"{next(c['text'] for c in conflicts if c['id'] == cid)}\", "
                         "והמחיר שלה כתוב בפתק.") if n == 1 else
                        "אין דרך לאכוף את זה בלי לשבור אילוץ חובה.")}


def await_principal(state: TimetableState):
    # ⏸ עצירה לאישור אדם #2: המנהלת לוחצת על כפתור, כותבת, או מאשרת.
    msg = interrupt({"type": "decision", "conflicts": state.get("conflicts", [])})
    update = {"incoming": msg, "action": None, "simulation": None}
    if msg.get("kind") == "text":
        update["chat"] = [{"role": "principal", "text": msg["text"]}]
    return update


def interpret(state: TimetableState):
    text = state["incoming"]["text"]
    action = llm.interpret(text, state.get("conflicts", []), state.get("constraints", []))
    return {"action": action.model_dump(), "chat": llm_notice()}


def clarify(state: TimetableState):
    # ⏸ עצירה #3: שאלת הבהרה. התשובה מצורפת לטקסט המקורי ומפוענחת שוב.
    q = state["action"]["question"]
    reply = interrupt({"type": "clarify", "question": q})
    if isinstance(reply, dict):
        reply = reply.get("text", "")
    merged = state["incoming"]["text"] + " " + reply
    return {"incoming": {"kind": "text", "text": merged},
            "chat": say(q) + [{"role": "principal", "text": reply}]}


def answer(state: TimetableState):
    """עונה על שאלה של המנהלת, רק לפי הנתונים של המערכת שנבנתה."""
    a = state.get("action") or {}
    if a.get("type") == "info":
        # תשובה ישירה מהמודל (למשל: "הכלל הזה כבר קיים")
        return {"chat": llm_notice() + say(a.get("reply") or a.get("summary") or "")}
    text = state["incoming"]["text"]
    teachers = D.find_teachers(text)
    classes = D.find_classes(text)
    lessons = state["result"].get("lessons", [])

    def schedule(match):
        lines = []
        for d, day in enumerate(D.DAYS):
            items = sorted((l for l in lessons if l["day"] == d and match(l)), key=lambda l: l["period"])
            lines.append(f"{day}: " + (", ".join(f"שעה {l['period'] + 1} {l['subject']} ({l['cls']})"
                                                  for l in items) or "חופשי"))
        return "\n".join(lines)

    if not teachers and not classes:
        return {"chat": say("על איזו מורה או כיתה השאלה? כתבי את השם, ואענה לפי המערכת.")}

    # 1. שולפים את הנתונים הרלוונטיים בלבד
    parts = []
    for t in teachers:
        parts.append(f"המערכת של {t}:\n" + schedule(lambda l, t=t: t in l["teachers"]))
    for c in classes:
        parts.append(f"המערכת של כיתה {c}:\n" + schedule(lambda l, c=c: l["cls"] == c))
    related = [x["text"] for x in state["constraints"]
               if any(n in x.get("text", "") for n in teachers + classes) or x.get("source") == "rule"]
    parts.append("כללים ובקשות רלוונטיים: " + "; ".join(related))
    context = "\n\n".join(parts)

    # 2. מודל השפה עונה לפי הנתונים. במצב הדגמה: מציגים את הנתונים עצמם.
    reply = llm.answer(text, context) or context.split("\n\nכללים")[0]
    return {"chat": llm_notice() + say(reply)}


def simulate(state: TimetableState):
    a = state["action"]
    constraints, pins = list(state["constraints"]), list(state.get("pins", []))
    new_ids = []
    if a["type"] == "add_rule":
        rules = [r for r in a.get("rules") or [] if r.get("matched") and r.get("kind")]
        if not rules:
            return {"simulation": None,
                    "chat": say("לא מצאתי כלל שמתאים לבקשה. נסי לנסח אותה אחרת.")}
        for r in rules:
            cid = f"C{len(constraints) + 1}"
            new_ids.append(cid)
            constraints.append({"id": cid, "kind": r["kind"], "params": r["params"],
                                "text": r["summary"], "source": "chat"})
    elif a["type"] == "move_lesson":
        mv = a.get("move") or {}
        if mv.get("cls") not in D.CLASSES or mv.get("subject") not in D.CLASS_CURRICULUM[mv["cls"]] \
                or not (0 <= mv.get("day", -1) < 6) or not (0 <= mv.get("period", -1) < D.PERIODS_PER_DAY[mv["day"]]):
            return {"simulation": None,
                    "chat": say("לא הצלחתי להבין בדיוק איזה שיעור להזיז ולאן. כתבי כיתה, מקצוע, יום ושעה.")}
        pins.append(mv)
    sim = solver.solve(constraints, pins, time_limit=TRIAL_TIME_LIMIT, previous=state["result"]["lessons"])
    if sim["status"] == "infeasible":
        return {"simulation": None,
                "chat": say(f"הבנתי: {a['summary']}. אבל זה בלתי אפשרי יחד עם אילוצי החובה, ולכן לא שיניתי דבר.")}
    old = state["result"]
    simulation = {
        "summary": a["summary"],
        "moved": solver.diff_lessons(old["lessons"], sim["lessons"]),
        # המחיר: רק כללים קיימים שנפגעו. הכלל החדש עצמו הוא לא "מחיר".
        "added": [v for v in solver.diff_violations(old["violations"], sim["violations"])
                  if v["id"] not in new_ids],
        "constraints": constraints, "pins": pins,
    }
    chat = []
    if a.get("unhandled"):
        chat = say(f"שימי לב: את החלק הזה עוד לא ביצעתי: \"{a['unhandled']}\". כתבי אותו בהודעה נפרדת אחרי האישור.")
    return {"simulation": simulation, "chat": chat}


def confirm(state: TimetableState):
    # ⏸ עצירה #4: "זה מה שישתנה. לאשר?"
    sim = state["simulation"]
    ok = interrupt({"type": "confirm", "summary": sim["summary"], "moved": sim["moved"],
                    "added": [{"text": a["text"], "count": len(a["instances"])} for a in sim["added"]]})
    return {"incoming": {"kind": "confirm", "ok": bool(ok)}}


def apply_action(state: TimetableState):
    sim = state["simulation"]
    return {"constraints": sim["constraints"], "pins": sim["pins"],
            "chat": say(f"בוצע: {sim['summary']}. בונה מחדש...")}


def apply_decision(state: TimetableState):
    msg = state["incoming"]
    if msg.get("kind") == "text":     # החלטה שהגיעה מהצ'אט
        msg = {"conflict_id": state["action"]["conflict_id"], "option": state["action"]["option"]}
    cid, option = msg["conflict_id"], msg["option"]
    conflict = next((c for c in state.get("conflicts", []) if c["id"] == cid), None)
    if conflict is None:
        return {"chat": say("לא מצאתי את החריגה הזאת.")}
    keys = [i["key"] for i in conflict["instances"]]
    forbidden = {}
    new = []
    for c in state["constraints"]:
        if c["id"] == cid:
            c = dict(c)
            if option == "waive":
                c["waived"] = list(c.get("waived", [])) + keys
            elif option.startswith("alt:"):
                # דרך שהמנהלת בחרה: אוכפים את הכלל, וגם אוסרים את המחירים של הדרכים הקודמות
                c["hard"] = True
                chosen = next(o for o in conflict["options"] if o["id"] == option)
                for fid, fkeys in chosen.get("forbid", {}).items():
                    forbidden[fid] = fkeys
            elif option == "alt_day":
                c["params"] = {**c["params"], "day": c["alt_day"]}
                c["text"] = f"{c['params']['teacher']}: יום {D.DAYS[c['alt_day']]} חופשי (חלופי)"
                c["alt_day"] = None
        new.append(c)
    if forbidden:
        new = [dict(c, hard_keys=list(c.get("hard_keys", [])) + forbidden[c["id"]]) if c["id"] in forbidden else c
               for c in new]
    label = next(o["label"] for o in conflict["options"] if o["id"] == option)
    return {"constraints": new, "chat": say(f"החלטה: {conflict['text']} ← {label}")}


def finalize(state: TimetableState):
    return {"published": True, "conflicts": [],
            "chat": say("המערכת אושרה ופורסמה למורות. אפשר להמשיך לבקש תיקונים בצ'אט.")}


# =====================================================================
# 3. פונקציות ניתוב: מחליטות לאן ממשיכים (ענפים מותנים)
# =====================================================================

def route_after_solve(state: TimetableState):
    if state["result"]["status"] == "infeasible":
        return "diagnose"
    if state["result"]["violations"]:
        return "explain"
    return "await_principal"


def route_message(state: TimetableState):
    kind = state["incoming"].get("kind")
    if kind == "button":
        if state["incoming"].get("option") == "show_alternatives":
            return "alternatives"
        return "apply_decision"
    if kind == "approve":
        return "finalize"
    return "interpret"


def route_action(state: TimetableState):
    t = state["action"]["type"]
    if t == "decide" and state["action"].get("option") == "show_alternatives":
        return "alternatives"
    return {"decide": "apply_decision", "add_rule": "simulate", "move_lesson": "simulate",
            "question": "answer", "info": "answer", "approve": "finalize", "unclear": "clarify"}[t]


def route_after_simulate(state: TimetableState):
    return "confirm" if state.get("simulation") else "await_principal"


def route_after_confirm(state: TimetableState):
    return "apply_action" if state["incoming"]["ok"] else "await_principal"


# =====================================================================
# 4. בניית הגרף: צמתים + קשתות
# =====================================================================

def build_graph():
    g = StateGraph(TimetableState)
    for name, fn in [
        ("load_data", load_data), ("translate_notes", translate_notes),
        ("review_translations", review_translations), ("solve", solve),
        ("diagnose", diagnose), ("explain", explain), ("await_principal", await_principal),
        ("interpret", interpret), ("clarify", clarify), ("answer", answer),
        ("simulate", simulate), ("confirm", confirm), ("apply_action", apply_action),
        ("apply_decision", apply_decision), ("finalize", finalize),
        ("alternatives", alternatives),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "load_data")
    g.add_edge("load_data", "translate_notes")
    g.add_edge("translate_notes", "review_translations")
    g.add_edge("review_translations", "solve")

    g.add_conditional_edges("solve", route_after_solve, ["diagnose", "explain", "await_principal"])
    g.add_edge("diagnose", "await_principal")
    g.add_edge("explain", "await_principal")

    g.add_conditional_edges("await_principal", route_message,
                            ["apply_decision", "alternatives", "finalize", "interpret"])
    g.add_edge("alternatives", "await_principal")   # חוזרים לאותה עצירה, עם הפתק המעודכן
    g.add_conditional_edges("interpret", route_action,
                            ["apply_decision", "alternatives", "simulate", "answer", "finalize", "clarify"])
    g.add_edge("clarify", "interpret")
    g.add_edge("answer", "await_principal")
    g.add_conditional_edges("simulate", route_after_simulate, ["confirm", "await_principal"])
    g.add_conditional_edges("confirm", route_after_confirm, ["apply_action", "await_principal"])

    g.add_edge("apply_action", "solve")      # לולאה
    g.add_edge("apply_decision", "solve")    # לולאה
    g.add_edge("finalize", "await_principal")

    # ה-checkpointer שומר את המצב אחרי כל צומת, ולכן אפשר לעצור ולהמשיך.
    # בהדגמה: בזיכרון. בגרסה האמיתית: במסד הנתונים.
    return g.compile(checkpointer=InMemorySaver())


graph = build_graph()


# =====================================================================
# גרף קטן נוסף: תרגום בקשה חופשית של מורה, עם אישור שלה
# =====================================================================

class TeacherState(TypedDict, total=False):
    teacher: str
    text: str
    proposal: dict
    confirmed: bool


def t_translate(state: TeacherState):
    p = llm.translate_note(f"{state['teacher']}: {state['text']}")
    llm.take_failure()  # למורה לא מציגים הודעה טכנית; רק מאפסים את הסימון
    return {"proposal": p.model_dump()}


def t_confirm(state: TeacherState):
    ok = interrupt({"type": "teacher_confirm", "proposal": state["proposal"]})
    return {"confirmed": bool(ok)}


def build_teacher_graph():
    g = StateGraph(TeacherState)
    g.add_node("translate", t_translate)
    g.add_node("confirm", t_confirm)
    g.add_edge(START, "translate")
    g.add_edge("translate", "confirm")
    g.add_edge("confirm", END)
    return g.compile(checkpointer=InMemorySaver())


teacher_graph = build_teacher_graph()
