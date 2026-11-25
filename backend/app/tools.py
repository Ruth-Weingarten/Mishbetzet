"""
הכלים של הסוכן בצ'אט.

מודל השפה לא מקבל "טופס למילוי". הוא מקבל כלים קטנים, מחליט בעצמו מה להפעיל, רואה את התוצאה,
ומחליט מה הלאה (זו לולאה בגרף: agent -> tools -> agent).

שתי קבוצות:
  כלי קריאה   רצים מיד. הם רק מחזירים נתונים, והחישובים (חלונות, ספירות) נעשים כאן בקוד, לא במודל.
  כלי שינוי   propose_rule / propose_move / rebuild. הם לא משנים כלום בעצמם: הם מכינים "פעולה"
              שעוברת בגרף להדמיה, לעצירה לאישור של המנהלת, ורק אחר כך לפותר.

כל כלי מוגדר כמחלקת Pydantic: השם הוא שם הכלי, התיעוד הוא התיאור שהמודל רואה, והשדות הם הפרמטרים.
"""

from typing import Optional

from pydantic import BaseModel, Field

from . import data as D

MAX_LINES = 40


# =====================================================================
# 1. מה שהמודל רואה: שם, תיאור ופרמטרים של כל כלי
# =====================================================================

class get_violations(BaseModel):
    """הכללים שלא קוימו במערכת הנוכחית ובאילו מורות וכיתות. אפשר לסנן למורה אחת."""
    teacher: Optional[str] = Field(None, description="שם מורה (משפחה פרטי) לסינון, או ריק לכל המורות")


class get_teacher_schedule(BaseModel):
    """המערכת של מורה: השיעורים בכל יום, החלונות בכל יום וסך החלונות בשבוע."""
    teacher: str = Field(description="שם המורה (משפחה פרטי)")


class get_class_schedule(BaseModel):
    """המערכת של כיתה: השיעורים בכל יום."""
    cls: str = Field(description="שם הכיתה, למשל ג'2")


class get_teacher_stats(BaseModel):
    """טבלת מורות ממוינת לפי מדד: חלונות, ימי עבודה, ימים עם שיעור בודד. מתאים ל'למי יש הכי הרבה...'."""
    sort_by: str = Field("gaps", description="gaps=חלונות בשבוע, days=ימי עבודה, single_lesson_days=ימים עם שיעור אחד, lessons=שיעורים")
    top: int = Field(10, description="כמה מורות להציג")


class list_rules(BaseModel):
    """כל הכללים והבקשות הפעילים עכשיו (של בית הספר ושל המנהלת)."""


class find_lessons(BaseModel):
    """חיפוש שיעורים לפי כל שילוב של מורה, כיתה, מקצוע, יום ושעה. שדה ריק = בלי סינון."""
    teacher: Optional[str] = None
    cls: Optional[str] = Field(None, description="למשל ה'1")
    subject: Optional[str] = Field(None, description="שם המקצוע או חלק ממנו")
    day: Optional[int] = Field(None, description="0=ראשון ... 5=שישי")
    period: Optional[int] = Field(None, description="0=שעה ראשונה ... 6=שביעית")


class find_free_slots(BaseModel):
    """שעות פנויות של מורה, ואיזה מהן צמודות לשיעור קיים (ולכן לא יוצרות חלון)."""
    teacher: str
    day: Optional[int] = Field(None, description="0=ראשון ... 5=שישי, או ריק לכל הימים")


class get_teacher_info(BaseModel):
    """סיכום על מורה: כמה שיעורים, באילו ימים, אילו כיתות ומקצועות."""
    teacher: str


class propose_rule(BaseModel):
    """מציע כלל חדש מהרשימה הסגורה. לא משנה כלום: המערכת תריץ הדמיה, תראה למנהלת מה ישתנה ותבקש אישור.
    אפשר לקרוא לכלי כמה פעמים אם יש כמה כללים. בחרי את סוג הכלל הקרוב ביותר לכוונה והגבילי אותו למורה/יום."""
    kind: str = Field(description="סוג הכלל, אחד מהרשימה שבהנחיה")
    params: dict = Field(description="הפרמטרים של הסוג, כולל teachers/days להגבלה")
    summary: str = Field(description="משפט קצר בעברית: מה הכלל יבצע בפועל")


class propose_move(BaseModel):
    """מציע להזיז שיעור מסוים למשבצת מסוימת. לא משנה כלום: עובר הדמיה ואישור של המנהלת."""
    cls: str
    subject: str = Field(description="שם המקצוע בדיוק כמו בכיתה")
    day: int = Field(description="0=ראשון ... 5=שישי")
    period: int = Field(description="0=שעה ראשונה ... 6=שביעית")
    summary: str = Field(description="משפט קצר בעברית: מה מזיזים ולאן")


class rebuild(BaseModel):
    """מבקש לבנות את המערכת מחדש לפי הכללים הנוכחיים. עובר אישור של המנהלת. השתמשי רק כשביקשו במפורש."""
    reason: Optional[str] = None


READ_TOOLS = [get_violations, get_teacher_schedule, get_class_schedule, get_teacher_stats,
              list_rules, find_lessons, find_free_slots, get_teacher_info]
CHANGE_TOOLS = [propose_rule, propose_move, rebuild]
ALL_TOOLS = READ_TOOLS + CHANGE_TOOLS
_SCHEMAS = {t.__name__: t for t in ALL_TOOLS}


# =====================================================================
# 2. עזרים
# =====================================================================

def _lessons(state):
    return (state.get("result") or {}).get("lessons", [])


def _teacher(name):
    """שם מלא של מורה לפי מה שהמודל כתב. מחזיר (שם, שגיאה)."""
    if not name:
        return None, "חסר שם מורה."
    if name in D.TEACHERS:
        return name, None
    found = D.find_teachers(name)
    if len(found) == 1:
        return found[0], None
    if len(found) > 1:
        return None, f"יש כמה מורות שמתאימות: {', '.join(found)}. צריך שם מלא."
    return None, f"לא מצאתי מורה בשם {name}."


def _class(name):
    if name in D.CLASSES:
        return name, None
    found = D.find_classes(name or "")
    if len(found) == 1:
        return found[0], None
    return None, f"לא מצאתי כיתה בשם {name}."


def _by_day(lessons, t):
    """יום -> קבוצת שעות שבהן המורה עובדת."""
    out = {}
    for l in lessons:
        if t in l["teachers"]:
            out.setdefault(l["day"], set()).add(l["period"])
    return out


def _gaps(periods):
    ps = sorted(periods)
    return [p for p in range(ps[0], ps[-1]) if p not in ps] if ps else []


def _cut(lines):
    if len(lines) > MAX_LINES:
        return lines[:MAX_LINES] + [f"... ועוד {len(lines) - MAX_LINES}"]
    return lines


# =====================================================================
# 3. כלי הקריאה
# =====================================================================

def _get_violations(state, teacher=None):
    t = None
    if teacher:
        t, err = _teacher(teacher)
        if err:
            return err
    rows = []
    for v in (state.get("result") or {}).get("violations", []):
        items = [i["label"] for i in v["instances"] if t is None or t in i["label"]]
        if items:
            shown = ", ".join(items[:8]) + (f" ועוד {len(items) - 8}" if len(items) > 8 else "")
            rows.append(f"{v['text']}: {len(items)} מקרים ({shown})")
    if not rows:
        return "אין חריגות" + (f" אצל {t}." if t else ".")
    out = _cut(rows)
    if t is None:
        # סיכום לפי מורה: מי נפגעה ובכמה מקרים (התוויות נושאות את שם המורה)
        per = {}
        for v in (state.get("result") or {}).get("violations", []):
            for i in v["instances"]:
                for name in D.TEACHERS:
                    if name in i["label"]:
                        per[name] = per.get(name, 0) + 1
        if per:
            top = sorted(per.items(), key=lambda x: -x[1])[:15]
            out.append("מורות עם חריגות (מספר מקרים): " + ", ".join(f"{n} ({c})" for n, c in top))
    return "\n".join(out)


def _get_teacher_schedule(state, teacher):
    t, err = _teacher(teacher)
    if err:
        return err
    lessons = _lessons(state)
    lines, total = [f"המערכת של {t}:"], 0
    for d, day in enumerate(D.DAYS):
        items = sorted((l for l in lessons if l["day"] == d and t in l["teachers"]), key=lambda l: l["period"])
        line = f"{day}: " + (", ".join(f"שעה {l['period'] + 1} {l['subject']} ({l['cls']})" for l in items) or "חופשי")
        free = [p + 1 for p in _gaps({l["period"] for l in items})]
        total += len(free)
        if free:
            line += f"  ← חלונות: {len(free)} (שעות {', '.join(map(str, free))})"
        lines.append(line)
    lines.append(f"סך החלונות בשבוע: {total}")
    return "\n".join(lines)


def _get_class_schedule(state, cls):
    c, err = _class(cls)
    if err:
        return err
    lessons = _lessons(state)
    lines = [f"המערכת של כיתה {c}:"]
    for d, day in enumerate(D.DAYS):
        items = sorted((l for l in lessons if l["day"] == d and l["cls"] == c), key=lambda l: l["period"])
        lines.append(f"{day}: " + (", ".join(f"שעה {l['period'] + 1} {l['subject']}" for l in items) or "אין שיעורים"))
    return "\n".join(lines)


def _stats(lessons):
    rows = {}
    for t in D.TEACHERS:
        days = _by_day(lessons, t)
        rows[t] = {
            "lessons": sum(len(p) for p in days.values()),
            "days": len(days),
            "gaps": sum(len(_gaps(p)) for p in days.values()),
            "single_lesson_days": sum(1 for p in days.values() if len(p) == 1),
        }
    return rows


def _get_teacher_stats(state, sort_by="gaps", top=10):
    if sort_by not in ("gaps", "days", "single_lesson_days", "lessons"):
        return "sort_by חייב להיות אחד מ: gaps, days, single_lesson_days, lessons."
    rows = _stats(_lessons(state))
    ranked = sorted(((t, r) for t, r in rows.items() if r["lessons"]), key=lambda x: -x[1][sort_by])[:max(1, min(top, 30))]
    lines = [f"{t}: חלונות {r['gaps']}, ימי עבודה {r['days']}, שיעורים {r['lessons']}, ימים עם שיעור בודד {r['single_lesson_days']}"
             for t, r in ranked]
    return "\n".join(lines) or "אין נתונים."


def _list_rules(state):
    lines = []
    for c in state.get("constraints", []):
        who = "בקשה מהצ'אט" if c.get("source") == "chat" else "כלל"
        lines.append(f"- [{who}] {c.get('text', c.get('kind'))}")
    return "\n".join(_cut(lines)) or "אין כללים פעילים."


def _find_lessons(state, teacher=None, cls=None, subject=None, day=None, period=None):
    t = c = None
    if teacher:
        t, err = _teacher(teacher)
        if err:
            return err
    if cls:
        c, err = _class(cls)
        if err:
            return err
    rows = []
    for l in sorted(_lessons(state), key=lambda l: (l["day"], l["period"], l["cls"])):
        if t and t not in l["teachers"]:
            continue
        if c and l["cls"] != c:
            continue
        if subject and subject not in l["subject"]:
            continue
        if day is not None and l["day"] != day:
            continue
        if period is not None and l["period"] != period:
            continue
        rows.append(f"{D.DAYS[l['day']]} שעה {l['period'] + 1}: {l['cls']} {l['subject']} ({', '.join(l['teachers']) or 'ללא מורה'})")
    return "\n".join(_cut(rows)) or "לא נמצאו שיעורים."


def _find_free_slots(state, teacher, day=None):
    t, err = _teacher(teacher)
    if err:
        return err
    days = _by_day(_lessons(state), t)
    lines = []
    for d in ([day] if day is not None else range(len(D.DAYS))):
        if not 0 <= d < len(D.DAYS):
            return "יום לא תקין."
        busy = days.get(d, set())
        if not busy:
            lines.append(f"{D.DAYS[d]}: יום חופשי. שיעור חדש יוסיף לה יום עבודה.")
            continue
        free = [p for p in range(D.PERIODS_PER_DAY[d]) if p not in busy]
        adjacent = [p + 1 for p in free if p - 1 in busy or p + 1 in busy]
        gap_makers = [p + 1 for p in free if p + 1 not in adjacent]
        lines.append(f"{D.DAYS[d]}: שעות פנויות {', '.join(str(p + 1) for p in free) or 'אין'}. "
                     f"צמודות לשיעור קיים (לא יוצרות חלון): {', '.join(map(str, adjacent)) or 'אין'}. "
                     f"היו יוצרות חלון: {', '.join(map(str, gap_makers)) or 'אין'}")
    return "\n".join(lines)


def _get_teacher_info(state, teacher):
    t, err = _teacher(teacher)
    if err:
        return err
    mine = [l for l in _lessons(state) if t in l["teachers"]]
    if not mine:
        return f"{t}: אין לה שיעורים במערכת הנוכחית."
    days = _by_day(mine, t)
    free_days = [D.DAYS[d] for d in range(len(D.DAYS)) if d not in days]
    return (f"{t}: {len(mine)} שיעורים, עובדת {len(days)} ימים ({', '.join(D.DAYS[d] for d in sorted(days))}). "
            f"ימים חופשיים: {', '.join(free_days) or 'אין'}. "
            f"כיתות: {', '.join(sorted({l['cls'] for l in mine}))}. "
            f"מקצועות: {', '.join(sorted({l['subject'] for l in mine}))}.")


_READ = {
    "get_violations": _get_violations, "get_teacher_schedule": _get_teacher_schedule,
    "get_class_schedule": _get_class_schedule, "get_teacher_stats": _get_teacher_stats,
    "list_rules": _list_rules, "find_lessons": _find_lessons,
    "find_free_slots": _find_free_slots, "get_teacher_info": _get_teacher_info,
}


# =====================================================================
# 4. כלי השינוי: בודקים תקינות ומכינים פעולה. לא משנים כלום.
# =====================================================================

# סוג כלל -> פרמטרים חובה
RULE_REQUIRED = {
    "free_day": ["teacher", "day"],
    "teacher_not_periods": ["teachers", "periods"],
    "teacher_end_by": ["teacher", "day", "last_period"],
    "teacher_start_from": ["teacher", "day", "first_period"],
    "subject_days": ["subject", "days"],
    "no_double": ["subject"],
    "spread": ["subject"],
    "teacher_gaps": ["max_per_day"],
    "max_gaps_per_week": ["max"],
    "min_lessons_per_day": ["min"],
    "max_work_days": ["threshold", "above", "below"],
    "short_day_early": ["max_lessons", "last_period"],
    "teacher_latest_start": ["max_start"],
    "subject_max_per_day": ["max"],
}


def _subject(name):
    if name in D.CURRICULUM:
        return name, None
    close = [s for s in D.CURRICULUM if name and (name in s or s in name)]
    if len(close) == 1:
        return close[0], None
    return None, f"המקצוע {name} לא קיים. המקצועות: {', '.join(D.CURRICULUM)}."


def _int_list(value, lo, hi, label):
    items = value if isinstance(value, list) else [value]
    try:
        items = [int(x) for x in items]
    except (TypeError, ValueError):
        return None, f"{label} חייבים להיות מספרים."
    if any(not lo <= x <= hi for x in items):
        return None, f"{label} חייבים להיות בין {lo} ל-{hi}."
    return items, None


def _check_rule(kind, params):
    """בודק ומנרמל פרמטרים של כלל. מחזיר (params, שגיאה)."""
    if kind not in RULE_REQUIRED:
        return None, f"סוג הכלל {kind} לא קיים. הסוגים: {', '.join(RULE_REQUIRED)}."
    p = dict(params or {})
    missing = [k for k in RULE_REQUIRED[kind] if k not in p]
    if missing:
        return None, f"חסרים פרמטרים לכלל {kind}: {', '.join(missing)}."
    if "teacher" in p:
        p["teacher"], err = _teacher(p["teacher"])
        if err:
            return None, err
    if p.get("teachers"):
        names = p["teachers"] if isinstance(p["teachers"], list) else [p["teachers"]]
        fixed = []
        for n in names:
            n, err = _teacher(n)
            if err:
                return None, err
            fixed.append(n)
        p["teachers"] = fixed
    else:
        p.pop("teachers", None)
    if "subject" in p:
        p["subject"], err = _subject(p["subject"])
        if err:
            return None, err
    for key, hi, label in (("day", 5, "ימים"), ("last_period", 6, "שעות"), ("first_period", 6, "שעות")):
        if key in p:
            v, err = _int_list(p[key], 0, hi, label)
            if err:
                return None, err
            p[key] = v[0]
    for key, hi, label in (("days", 5, "ימים"), ("periods", 6, "שעות")):
        if p.get(key) is not None:
            v, err = _int_list(p[key], 0, hi, label)
            if err:
                return None, err
            p[key] = v
        else:
            p.pop(key, None)
    return p, None


def _propose_rule(state, kind, params, summary):
    p, err = _check_rule(kind, params)
    if err:
        return err, None
    return "הכלל הוכן. המערכת תריץ הדמיה ותבקש מהמנהלת אישור.", \
           {"type": "add_rule", "rules": [{"matched": True, "kind": kind, "params": p, "summary": summary}],
            "summary": summary}


def _propose_move(state, cls, subject, day, period, summary):
    c, err = _class(cls)
    if err:
        return err, None
    if subject not in D.CLASS_CURRICULUM[c]:
        close = [s for s in D.CLASS_CURRICULUM[c] if subject in s or s in subject]
        if len(close) != 1:
            return f"לכיתה {c} אין מקצוע {subject}. המקצועות: {', '.join(D.CLASS_CURRICULUM[c])}.", None
        subject = close[0]
    if not 0 <= day < len(D.DAYS) or not 0 <= period < D.PERIODS_PER_DAY[day]:
        return "יום או שעה לא תקינים.", None
    return "ההעברה הוכנה. המערכת תריץ הדמיה ותבקש מהמנהלת אישור.", \
           {"type": "move_lesson", "move": {"cls": c, "subject": subject, "day": day, "period": period},
            "summary": summary}


def run_tool(name, args, state):
    """מריץ כלי אחד. מחזיר (טקסט שחוזר למודל, פעולה לגרף או None)."""
    schema = _SCHEMAS.get(name)
    if schema is None:
        return f"אין כלי בשם {name}.", None
    try:
        args = schema(**(args or {})).model_dump()
    except Exception as e:
        return f"הפרמטרים של {name} לא תקינים: {e}", None
    try:
        if name in _READ:
            return _READ[name](state, **args), None
        if name == "propose_rule":
            return _propose_rule(state, **args)
        if name == "propose_move":
            return _propose_move(state, **args)
        if name == "rebuild":
            return "הבנייה מחדש הוכנה. המנהלת תתבקש לאשר.", {"type": "rebuild", "summary": "בנייה מחדש"}
    except Exception as e:
        return f"הכלי {name} נכשל: {type(e).__name__}: {e}", None
    return "כלי לא מוכר.", None


def merge_action(current, new):
    """כמה כלי שינוי באותה הודעה: כללים מתאחדים, ושינוי מסוג אחר נדחה להודעה נפרדת."""
    if current is None:
        return current if new is None else new, None
    if new is None:
        return current, None
    if current["type"] == "add_rule" and new["type"] == "add_rule":
        merged = dict(current, rules=current["rules"] + new["rules"],
                      summary=f"{current['summary']}; {new['summary']}")
        return merged, None
    return current, new
