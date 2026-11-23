"""
נתוני בית הספר: מבוססים על בית ספר בית יעקב אמיתי (49 כיתות, כ-90 מורות), לפי מערכת תשפ"ז.
המבנה, המקצועות, השעות וחלוקת העבודה אמיתיים. כל שמות המורות בדויים.

בהמשך הנתונים האלה יעברו למסד נתונים.
"""

import json
import re
from pathlib import Path

DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"]

# מספר המשבצות בכל יום (ראשון עד שישי). יום שישי קצר.
# לא כל כיתה ממלאת את כל המשבצות: כיתה א' לומדת 29 שעות, כיתה ח' 37.
PERIODS_PER_DAY = [7, 7, 7, 7, 7, 4]

# שעות השיעורים: (התחלה, סיום)
PERIOD_TIMES = [
    ("08:00", "08:45"),
    ("08:45", "09:30"),
    ("09:45", "10:30"),
    ("10:30", "11:15"),
    ("11:30", "12:15"),
    ("12:15", "13:00"),
    ("13:00", "13:45"),
]

# ---------------------------------------------------------------------
# הנתונים של בית הספר: מתוך דוח הפעילויות של מערכת תשפ"ז
# (מי מלמדת מה, באיזו כיתה, כמה שעות). נוצר מהקובץ school.json.
# ---------------------------------------------------------------------
_RAW = json.loads((Path(__file__).parent / "school.json").read_text(encoding="utf-8"))

GRADES = ["א'", "ב'", "ג'", "ד'", "ה'", "ו'", "ז'", "ח'"]
CLASSES = _RAW["classes"]          # 49 כיתות
HOMEROOM = _RAW["homeroom"]        # המחנכת של כל כיתה


def grade_of(cls: str) -> str:
    return cls[:2]


# קבוצות מקצועות (משמשות לצבעים ולכללים כמו "קודש בשעה ראשונה")
_GROUPS = {
    "kodesh": ["תורה", "תורה/פרשה", "נביא", "דינים", "דינים ויהדות", "יהדות", "יהדות חברה",
               "פ. שבוע", "ב. תפילה", "פ. אבות"],
    "lang": ["עברית", "כתיב", "דקדוק", "ספרות", "הבנת הנקרא", "חיבור", "הבנת הנקרא + חיבור",
             "חיבור והבנה", "אנגלית", "תגבור קריאה", "סיוע בקריאה", "נושא"],
    "math": ["חשבון", "הנדסה", "חשבון והנדסה"],
    "science": ["טבע", "מולדת", "גאוגרפיה", "הסטוריה"],
}


def _group(subject: str) -> str:
    base = subject.split(" (")[0]
    for g, names in _GROUPS.items():
        if base in names:
            return g
    return "other"


VICE = ["פריד נחמה", "בלוך מלכה", "קלוגר הודיה"]   # הסגניות

_HE2EN = dict(zip("אבגדהוזחטיכלמנסעפצקרשתךםןףץ",
                  ["a", "b", "g", "d", "h", "v", "z", "ch", "t", "y", "k", "l", "m", "n", "s", "", "p",
                   "tz", "k", "r", "sh", "t", "ch", "m", "n", "f", "tz"]))


def _email(name: str) -> str:
    """כתובת דוא"ל לדוגמה באותיות לטיניות: "פרנק נעמי" -> n.prnk@demo"""
    def tr(w):
        return "".join(_HE2EN.get(ch, "") for ch in w)
    parts = name.split()
    if len(parts) == 1:
        return f"{tr(parts[0])}@demo"
    return f"{tr(parts[-1])[:1]}.{tr(parts[0])}@demo"


# המורות. role: "vice" = סגנית מנהלת.
TEACHERS = {t: {"role": "vice" if t in VICE else None, "email": _email(t)} for t in _RAW["teachers"]}

# מי חינכה איזו כיתה בשנה שעברה (לכלל "לפתוח דף חדש" במאגר). אין נתונים כרגע.
PREV_HOMEROOM = {}


def _build():
    """
    טבלת השיבוץ: לכל (כיתה, מקצוע) מי מלמדת וכמה שעות.
    kind:     fixed = מורה אחת, parallel = כמה מורות באותה שעה (חצאי כיתה)
    block:    הקבצה: כמה כיתות לומדות את המקצוע באותה שעה, עם כמה מורות
    pullout:  שיעור סיוע: חלק מהתלמידות יוצאות, בזמן שהכיתה לומדת שיעור אחר
    rooms:    כמה חדרים מיוחדים השיעור תופס (מחשבים בחצאי כיתה: 2)
    """
    curriculum = {c: {} for c in CLASSES}
    assignment, blocks = {}, {}
    for i, it in enumerate(_RAW["items"]):
        s = it["subject"]
        block = None
        if len(it["classes"]) > 1:
            block = f"B{i}"
            blocks[block] = {"subject": s, "classes": it["classes"], "teachers": it["teachers"],
                             "hours": it["hours"]}
        for c in it["classes"]:
            curriculum[c][s] = it["hours"]
            assignment[(c, s)] = {
                "kind": "parallel" if len(it["teachers"]) > 1 else "fixed",
                "teachers": it["teachers"],
                "homeroom": it["teachers"] == [HOMEROOM[c]],
                "block": block,
                "pullout": it.get("pullout", False),
                "rooms": it.get("rooms", 1),
            }
    return curriculum, assignment, blocks


CLASS_CURRICULUM, ASSIGNMENT, BLOCKS = _build()

# כל המקצועות בבית הספר, עם קבוצה. CURRICULUM: מקצוע -> מספר השעות הגבוה ביותר בכיתה כלשהי.
SUBJECTS = {s: _group(s) for cur in CLASS_CURRICULUM.values() for s in cur}
CURRICULUM = {}
for _cur in CLASS_CURRICULUM.values():
    for _s, _h in _cur.items():
        CURRICULUM[_s] = max(CURRICULUM.get(_s, 0), _h)

# חדרים מיוחדים, וכמה שיעורים יכולים להתקיים בהם באותה שעה
ROOM_CAPACITY = {"אולם": 2, "חדר מחשבים": 2}
ROOMS = {s: "אולם" for s in SUBJECTS if s == "התעמלות"}
ROOMS.update({s: "חדר מחשבים" for s in SUBJECTS if "מחשבים" in s})

HOMEROOM_SUBJECTS = sorted({s for (c, s), a in ASSIGNMENT.items() if a["homeroom"]})


# טפסי המורות. מבוסס על הטופס האמיתי של בית הספר.
# בהדגמה הם נשמרים בזיכרון: מורה שממלאת טופס באתר מעדכנת את המילון הזה.
def _form(free_day=None, alt_day=None, subjects=(), blocked_class=None, reason="",
          leave=False, leave_when="", reduce_hours=0, free_text="", confirmed_rule=None, submitted=True):
    return {"free_day": free_day, "alt_day": alt_day, "subjects": list(subjects),
            "blocked_class": blocked_class, "reason": reason,
            "leave": leave, "leave_when": leave_when, "reduce_hours": reduce_hours,
            "free_text": free_text, "confirmed_rule": confirmed_rule, "submitted": submitted}


def _subjects_of(t):
    return sorted({s for (c, s), a in ASSIGNMENT.items() if t in a["teachers"]})


_BASE_FORMS = {
    "נוסבוים פייגי":       _form("שלישי", None, _subjects_of("נוסבוים פייגי")),
    "קלוגר רחל":     _form("שלישי", None, _subjects_of("קלוגר רחל")),
    "כץנלבוגן טובה":       _form("חמישי", None, _subjects_of("כץנלבוגן טובה")),
    "שטרנברג בילא":        _form("רביעי", None, _subjects_of("שטרנברג בילא")),
    "מאירוביץ טובה":     _form("רביעי", None, _subjects_of("מאירוביץ טובה")),
    "פולק שרה":       _form("ראשון", None, _subjects_of("פולק שרה"),
                             free_text="אם אפשר, לצמצם את השעות שלי ליומיים"),
    "קלוגר הודיה":      _form(None, None, _subjects_of("קלוגר הודיה"), free_text="ביום חמישי עד 12",
                             confirmed_rule={"matched": True, "kind": "teacher_end_by",
                                             "params": {"teacher": "קלוגר הודיה", "day": 4, "last_period": 3},
                                             "summary": "קלוגר הודיה: ביום חמישי לסיים עד 11:15"}),
    "בירנבוים תמר": _form(None, None, _subjects_of("בירנבוים תמר"),
                              free_text="ביום שני אני מתחילה רק מ-11:15",
                              confirmed_rule={"matched": True, "kind": "teacher_start_from",
                                              "params": {"teacher": "בירנבוים תמר", "day": 1, "first_period": 4},
                                              "summary": "בירנבוים תמר: ביום שני להתחיל מ-11:30"}),
    "כהנוביץ אסנת":       _form(None, None, _subjects_of("כהנוביץ אסנת"), free_text="ביום ראשון עד 10:00",
                             confirmed_rule={"matched": True, "kind": "teacher_end_by",
                                             "params": {"teacher": "כהנוביץ אסנת", "day": 0, "last_period": 1},
                                             "summary": "כהנוביץ אסנת: ביום ראשון לסיים עד 09:30"}),
}


FORMS = {}   # מתמלא בסוף הקובץ (_make_forms), אחרי שחושבו שעות המורות


def blocked():
    """כיתות שמורה סימנה בטופס שאינה יכולה ללמד."""
    return {t: [f["blocked_class"]] for t, f in FORMS.items() if f.get("blocked_class")}


# כללי בית הספר שהמנהלת סימנה מהרשימה (נשמרו מהשנה הקודמת)
SCHOOL_RULES = [
    {"id": "R1", "kind": "first_period_kodesh", "params": {"min_days": 4},
     "text": "מקצוע קודש בשעה הראשונה לפחות ב־4 מתוך 6 ימים בכל כיתה"},
    {"id": "R20", "kind": "teacher_free_day_base", "params": {"min_free_days": 1}, "hard": True,
     "text": "לכל מורה לפחות יום חופשי אחד בשבוע (אין מורה שעובדת 6 ימים)"},
    {"id": "R5", "kind": "subject_days", "params": {"subject": "פ. שבוע", "days": [2, 3, 4, 5]},
     "text": "פרשת שבוע מיום שלישי והלאה"},
    {"id": "R6", "kind": "no_double", "params": {"subject": "חשבון", "grades": GRADES[:5]},
     "text": "כיתות א'-ה' בלי שיעורי חשבון כפולים"},
    {"id": "R8", "kind": "teacher_gaps", "params": {"max_per_day": 1},
     "text": "לא יותר מחלון אחד ביום לכל מורה"},
    {"id": "R10", "kind": "min_lessons_per_day", "params": {"min": 2},
     "text": "מורה לא מגיעה ליום עם פחות משני שיעורים"},
    {"id": "R11", "kind": "max_gaps_per_week", "params": {"max": 2},
     "text": "לא יותר משני חלונות בשבוע לכל מורה"},
    {"id": "R12", "kind": "teacher_gaps", "params": {"max_per_day": 0, "days": [5]},
     "text": "אין חלונות ביום שישי"},
    {"id": "R13", "kind": "short_day_early", "params": {"max_lessons": 2, "last_period": 2},
     "text": "מורה שמגיעה לשני שיעורים בלבד: צמודים, ומסיימת עד 10:30"},
    {"id": "R14", "kind": "max_work_days", "params": {"threshold": 20, "above": 5, "below": 4},
     "text": "מורה עם יותר מ-20 שעות: עד 5 ימי עבודה. עד 20 שעות: עד 4 ימים"},
    {"id": "R18", "kind": "class_daily_load", "params": {"tolerance": 1, "friday_full": True}, "hard": True,
     "text": "יום לימודים סביר: מספר השיעורים של כיתה ביום קרוב לממוצע (ראשון עד חמישי), ושישי מלא (4 שעות)"},
    {"id": "R19", "kind": "teacher_max_wait", "params": {"max_wait": 1}, "hard": True,
     "text": "מורה לא ממתינה יותר משעה אחת בין שני שיעורים באותו יום"},
    {"id": "R2", "kind": "spread", "params": {"subject": "אנגלית"},
     "text": "אנגלית: לא יותר משיעור אחד ביום בכיתה"},
    {"id": "R3", "kind": "spread", "params": {"subject": "הסטוריה"},
     "text": "היסטוריה: לא שני שיעורים באותו יום"},
    {"id": "R4", "kind": "spread", "params": {"subject": "גאוגרפיה"},
     "text": "גאוגרפיה: לא שני שיעורים באותו יום"},
    {"id": "R7", "kind": "subject_days", "params": {"subject": "חשבון", "days": [0, 1, 2, 3, 4]},
     "text": "חשבון לא ביום שישי (היום הקצר)"},
    {"id": "R9", "kind": "subject_days", "params": {"subject": "אנגלית", "days": [0, 1, 2, 3, 4]},
     "text": "אנגלית לא ביום שישי"},
    {"id": "R15", "kind": "subject_days", "params": {"subject": "מלאכה", "days": [0, 1, 2, 3, 4]},
     "text": "מלאכה לא ביום שישי"},
    {"id": "R16", "kind": "subject_days", "params": {"subject": "מחשבים", "days": [0, 1, 2, 3, 4]},
     "text": "מחשבים לא ביום שישי"},
    {"id": "R17", "kind": "spread", "params": {"subject": "דקדוק"},
     "text": "דקדוק: לא שני שיעורים באותו יום"},
]

# הערות חופשיות של המנהלת (יתורגמו לכללים)
PRINCIPAL_NOTES = [
    {"id": "N1", "text": "סגניות: פריד, בלוך ובעיקר ה. קלוגר - לא לשבץ שעה ראשונה."},
    {"id": "N2", "text": "צירל נויפלד - ללא בקרים, ככל שניתן בארבעה ימים."},
    {"id": "N3", "text": "ברכה כגן - ללא בקרים."},
    {"id": "N4", "text": "צמח - לא יותר מ-5 שעות ביום בגלל התעמלות."},
    {"id": "N5", "text": "בארי - ככל שאפשר שתתחיל רק ב-8:00."},
    {"id": "N6", "text": "נעמי פרנק - ראשון ורביעי לסיים ב-11:00."},
    {"id": "N7", "text": "רבינוביץ - 4 ימים, שעות יותר מוקדמות."},
    {"id": "N8", "text": "אם החלפה של שעה בשנתון אחר יכולה להועיל - אפשרי בהתייעצות."},
    {"id": "N9", "text": "גולדשמידט יהודית - יום ראשון חופשי."},
    {"id": "N10", "text": "ווגל גאולה - לא לשבץ בשעה השביעית."},
    {"id": "N11", "text": "טורק שרה - ביום חמישי לסיים עד 12:15."},
    {"id": "N12", "text": "הלר מרים - ביום שלישי להתחיל רק מהשעה השלישית."},
    {"id": "N13", "text": "קנובלוך רבקה - ללא יום שישי."},
    {"id": "N14", "text": "שוורץ פערל - ביום שני בלי שעה ראשונה."},
    {"id": "N15", "text": "רייכמן חוה - ללא ימי שלישי."},
    {"id": "N16", "text": "תודה לכולן על שיתוף הפעולה, ושתהיה שנה טובה."},
    {"id": "N17", "text": "כדאי להתחשב ככל האפשר בבקשות של המורות הותיקות."},
]


def find_classes(text: str) -> list:
    """כיתות שמוזכרות בטקסט. מבינה גם בלי גרש: "א1", "כתה א 1", "א'1"."""
    found = []
    for g, n in re.findall(r"([א-ח])\s*['׳’`]?\s*(\d)", text):
        c = f"{g}'{n}"
        if c in CLASSES and c not in found:
            found.append(c)
    return found


def find_teachers(text: str) -> list:
    """
    מוצא שמות מורות בטקסט, רק כמילים שלמות.
    השמות שמורים כ"משפחה פרטי" (פרנק נעמי), אבל בטקסט כותבים גם "נעמי פרנק", "פרנק" או "ה. קלוגר".
    מותרות אותיות שימוש בתחילת המילה (ו, ב, ל, ה, מ, ש, כ).
    כשיש שתי מורות עם אותו שם משפחה, צריך גם את השם הפרטי (או האות הראשונה שלו).
    """
    def has(word):
        return re.search(rf"(?<![א-ת])[ובלהמשכ]{{0,2}}{re.escape(word)}(?![א-ת])", text)

    found = []
    for t in TEACHERS:
        parts = t.split()
        last, first = parts[0], " ".join(parts[1:])
        if last == "בן" and len(parts) > 2:           # שם משפחה כפול, כמו "בן דוד"
            last, first = " ".join(parts[:2]), " ".join(parts[2:])
        if not has(last):
            continue
        same_last = [x for x in TEACHERS if x.startswith(last + " ") or x == last]
        if len(same_last) == 1 or not first:
            found.append(t)
        elif has(first) or re.search(rf"(?<![א-ת]){re.escape(first[0])}\.\s*{re.escape(last)}", text):
            found.append(t)
    return found


def class_hours(c: str) -> int:
    """שעות שבועיות של כיתה (בלי שיעורי סיוע, שמתקיימים במקביל לשיעור אחר)."""
    return sum(h for s, h in CLASS_CURRICULUM[c].items() if not ASSIGNMENT[(c, s)]["pullout"])


def teacher_hours():
    """סך השעות השבועיות של כל מורה. בהקבצה המורה מלמדת פעם אחת, לא בכל כיתה."""
    hours = {t: 0 for t in TEACHERS}
    for (c, s), info in ASSIGNMENT.items():
        if info["block"] and BLOCKS[info["block"]]["classes"][0] != c:
            continue
        h = CLASS_CURRICULUM[c][s]
        for t in info["teachers"]:
            hours[t] += h / len(info["teachers"]) if info["kind"] == "pool" else h
    return {t: round(v) for t, v in hours.items()}


def data_problems():
    """
    בדיקות פשוטות של הנתונים, לפני שבונים: דברים שבגללם אי אפשר לבנות מערכת בכלל.
    מחזירה רשימת משפטים בשפה של המנהלת (ריקה = הכול תקין).
    """
    problems = []
    week = sum(PERIODS_PER_DAY)
    for c in CLASSES:
        need = class_hours(c)
        if need > week:
            problems.append(f"לכיתה {c} יש {need} שעות, ובשבוע יש רק {week} משבצות. צריך לתקן את המכוון.")
    for t, h in teacher_hours().items():
        if h > week:
            problems.append(f"לגב' {t} שובצו {h} שעות, ויש בשבוע רק {week} משבצות. "
                            "צריך להעביר חלק מהשעות שלה למורה אחרת, בלשונית \"שיבוץ\".")
    return problems


def school_snapshot():
    """כל נתוני בית הספר, בפורמט שהממשק יכול להציג."""
    hours = teacher_hours()
    return {
        "days": DAYS,
        "periodsPerDay": PERIODS_PER_DAY,
        "periodTimes": PERIOD_TIMES,
        "subjects": SUBJECTS,
        "curriculum": CURRICULUM,
        "classCurriculum": CLASS_CURRICULUM,
        "classes": CLASSES,
        "grades": GRADES,
        "homeroom": HOMEROOM,
        "teachers": [
            {"name": t, "role": v["role"], "email": v["email"], "hours": hours[t],
             "form": FORMS.get(t), "blocked": blocked().get(t, [])}
            for t, v in TEACHERS.items()
        ],
        "assignment": [
            {"cls": c, "subject": s, **info} for (c, s), info in ASSIGNMENT.items()
        ],
        "rules": SCHOOL_RULES,
        "notes": PRINCIPAL_NOTES,
        "problems": data_problems(),
    }


# ---------------------------------------------------------------------
# טפסים של כל המורות (שמות בדויים). חלק מהבקשות כבר מאושרות בתרגום,
# חלק נשארות טקסט חופשי שהמערכת לא מתרגמת לכלל, כמו אצל מורות אמיתיות.
# ---------------------------------------------------------------------

def _confirmed(kind, summary, params):
    return {"matched": True, "kind": kind, "params": params, "summary": summary}


def _end(t, day, last_period, label):
    return (f"ביום {DAYS[day]} לסיים עד {label}", _confirmed(
        "teacher_end_by", f"{t}: ביום {DAYS[day]} לסיים עד {PERIOD_TIMES[last_period][1]}",
        {"teacher": t, "day": day, "last_period": last_period}))


def _start(t, day, first_period, label):
    return (f"ביום {DAYS[day]} להתחיל מ-{label}", _confirmed(
        "teacher_start_from", f"{t}: ביום {DAYS[day]} להתחיל מ-{PERIOD_TIMES[first_period][0]}",
        {"teacher": t, "day": day, "first_period": first_period}))


def _not(t, periods, days, text, summary):
    params = {"teachers": [t], "periods": periods}
    if days:
        params["days"] = days
    return (text, _confirmed("teacher_not_periods", summary, params))


def _make_forms():
    import random
    rng = random.Random(5787)
    hours = teacher_hours()
    forms = dict(_BASE_FORMS)

    # בקשות חופשיות שהמורה אישרה את התרגום שלהן
    t = "אורנשטיין רחל";   forms[t] = ("ביום ראשון אני מתחילה רק מ-9:45",) + (_start(t, 0, 2, "9:45")[1],)
    t = "אייזנברג דבורה";  forms[t] = ("ביום רביעי אני חייבת לצאת ב-11:15",) + (_end(t, 3, 3, "11:15")[1],)
    t = "אלטמן עדינה";     forms[t] = _not(t, [0], [2], "בימי שלישי בלי שעה ראשונה, בבקשה",
                                           f"{t}: ביום שלישי לא בשעה הראשונה")
    t = "ארליך חנה";       forms[t] = _not(t, [6], None, "אני לא יכולה בשעה השביעית",
                                           f"{t}: לא בשעה השביעית")
    t = "בארי פנינה";      forms[t] = ("ביום חמישי לסיים ב-11:15",) + (_end(t, 4, 3, "11:15")[1],)
    t = "בוקסבוים מינדי";  forms[t] = ("ביום שני אפשר רק מ-11:30",) + (_start(t, 1, 4, "11:30")[1],)
    t = "ברגמן הודיה";     forms[t] = _not(t, [5, 6], [0, 2], "בימי ראשון ושלישי בלי שעות אחרי 12:15",
                                           f"{t}: בימי ראשון ושלישי לא בשעות 12:15 ואילך")
    t = "ברנדס תמר";       forms[t] = ("ביום שלישי עד 10:30",) + (_end(t, 2, 2, "10:30")[1],)
    t = "גוטליב שיינדי";   forms[t] = _not(t, [0], None, "לא להתחיל לפני 8:45",
                                           f"{t}: לא בשעה הראשונה")
    t = "גולדפרב אלישבע";  forms[t] = ("ביום רביעי מ-9:45",) + (_start(t, 3, 2, "9:45")[1],)
    t = "גוראריה קילא";    forms[t] = ("ביום שני אני מסיימת ב-10:30",) + (_end(t, 1, 2, "10:30")[1],)
    t = "דויטש גאולה";     forms[t] = ("ביום חמישי מתחילה ב-9:45",) + (_start(t, 4, 2, "9:45")[1],)
    t = "דרוק תהילה";      forms[t] = _not(t, [5, 6], None, "בלי שיעור בשעה השישית והשביעית",
                                           f"{t}: לא בשעות השישית והשביעית")
    t = "הורוביץ צפורה";   forms[t] = ("ביום שני לסיים ב-11:15",) + (_end(t, 1, 3, "11:15")[1],)
    t = "הכט זהבה";        forms[t] = ("ביום ראשון עד 10:30",) + (_end(t, 0, 2, "10:30")[1],)
    t = "וינברג רחל";      forms[t] = ("ביום שלישי מתחילה מ-9:45",) + (_start(t, 2, 2, "9:45")[1],)

    # מורות שהמערכת לא מתרגמת את הבקשה שלהן לכלל (נשארות הערה למנהלת)
    free_only = {
        "גינזבורג הודיה": "תודה רבה על ההתחשבות בשנים הקודמות!",
        "זילברמן עדינה": "אשמח ללמד שני שיעורים רצופים באותה כיתה",
        "חזן דבורה": "לפעמים אצטרך להחליף ימים בגלל אירועים במשפחה, אתאם בהמשך",
        "יפה חנה": "אני מעדיפה ללמד בקומה הראשונה",
        "ליבוביץ מרים": "תודה, ובבקשה לא יותר מארבעה שיעורים רצופים",
        "מילר תמר": "אשמח אם אפשר לשבץ אותי בשעה השלישית עם כיתה ו'",
        "סופר מרים": "תודה רבה!",
        "עמרם הניה": "אם אפשר ללמד את אותה כיתה באותה שעה בכל יום",
        "פוגל סימה": "אשמח להקל קצת בשעות, יש לי לימודים בערב",
        "צייטלין טליה": "אפשר לתאם איתי החלפות כשצריך, אני גמישה",
    }
    for t, txt in free_only.items():
        forms[t] = txt

    # מי שכבר יש לה טופס או בקשה: לא נוגעים. לשאר: מגרילים יום חופשי (קבוע, לפי זרע)
    explicit = set(forms)
    day_names = DAYS
    weights = [2, 2, 2, 2, 2, 3]
    out = {}
    for t in TEACHERS:
        if t == "משרה פנויה":
            continue
        v = forms.get(t)
        if isinstance(v, dict):
            out[t] = v
        elif isinstance(v, tuple):
            out[t] = _form(None, None, _subjects_of(t), free_text=v[0], confirmed_rule=v[1])
        elif isinstance(v, str):
            out[t] = _form(None, None, _subjects_of(t), free_text=v)
        else:
            free = None
            alt = None
            if hours.get(t, 0) < 23 and rng.random() < 0.52:
                d = rng.choices(range(6), weights)[0]
                free = day_names[d]
                if rng.random() < 0.6:
                    alt = day_names[rng.choice([x for x in range(6) if x != d])]
            out[t] = _form(free, alt, _subjects_of(t))

    # מורות שהמנהלת כתבה עליהן הערה: בלי יום חופשי נוסף מהטופס
    for t in ["גולדשמידט יהודית", "ווגל גאולה", "טורק שרה", "הלר מרים",
              "קנובלוך רבקה", "שוורץ פערל", "רייכמן חוה"]:
        if t in out:
            out[t]["free_day"] = None
            out[t]["alt_day"] = None

    # כמה בקשות מיוחדות נוספות בטופס עצמו
    def _upd(t, **kw):
        if t in out:
            out[t].update(kw)
    _upd("טננבוים זהבה", reduce_hours=2, reason="לימודים בערב")
    _upd("רייכמן חוה", leave=True, leave_when="בעוד חודש בערך, לשבוע")
    mine = sorted({c for (c, s_), a in ASSIGNMENT.items() if "שפירא סימה" in a["teachers"]})
    if mine:
        _upd("שפירא סימה", blocked_class=mine[0], reason="קרבה משפחתית לתלמידה")
    return out


FORMS.update(_make_forms())
