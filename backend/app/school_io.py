"""
ייבוא בית ספר מקובץ אקסל, ויצירת תבנית אקסל ריקה למילוי.

הקובץ מכיל ארבע לשוניות:
  הגדרות:  ימי לימוד ומספר השיעורים בכל יום
  כיתות:   שם כיתה ומחנכת (אפשר להשאיר ריק, ואז הכיתות נלקחות מלשונית השיעורים)
  מורות:   שם מורה
  שיעורים: מקצוע, כיתות, מורות, שעות בשבוע, חדר, שיעור סיוע

הפונקציה import_workbook בודקת את הקובץ ומחזירה רשימת שגיאות בעברית, עם מספרי שורות.
"""

import io
import json
import re

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import data as D

SHEET_SETTINGS, SHEET_CLASSES, SHEET_TEACHERS, SHEET_LESSONS, SHEET_HELP = "הגדרות", "כיתות", "מורות", "שיעורים", "הוראות"
ALL_DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"]


def _style(ws, widths):
    ws.sheet_view.rightToLeft = True
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="FFF2B3")
        c.alignment = Alignment(horizontal="right")


def make_template() -> bytes:
    """תבנית ריקה עם דוגמה קטנה בכל לשונית."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_HELP
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 110
    for line in [
        "איך ממלאים:",
        "1. לשונית 'הגדרות': לכל יום כותבים כמה שיעורים יש בו. יום בלי לימודים: משאירים 0 או ריק.",
        "2. לשונית 'כיתות': שם כל כיתה (למשל א'1) והמחנכת. אפשר להשאיר את הלשונית ריקה.",
        "3. לשונית 'מורות': שם כל מורה. מורה שמופיעה רק בלשונית השיעורים תתווסף לבד.",
        "4. לשונית 'שיעורים': שורה לכל מקצוע. אם כמה כיתות לומדות אותו יחד (הקבצה), כותבים אותן מופרדות בפסיק.",
        "   אם כמה מורות מלמדות יחד באותה שעה (למשל חצאי כיתה), כותבים אותן מופרדות בפסיק.",
        "   'שעות בשבוע': מספר שלם. 'חדר': רק אם צריך חדר מיוחד (אולם, חדר מחשבים). 'שיעור סיוע': כותבים כן.",
        "5. מעלים את הקובץ באתר, בלשונית 'בית הספר'. אם יש שגיאה, האתר יגיד באיזו שורה.",
        "השורות שבדוגמה הן להמחשה בלבד. אפשר למחוק אותן.",
    ]:
        ws.append([line])

    ws = wb.create_sheet(SHEET_SETTINGS)
    ws.append(["יום", "מספר שיעורים"])
    for d, n in zip(ALL_DAYS, [7, 7, 7, 7, 7, 4]):
        ws.append([d, n])
    ws.append([])
    ws.append(["שעת התחלה של השיעור הראשון", "08:00"])
    ws.append(["אורך שיעור בדקות", 45])
    _style(ws, [32, 16])

    ws = wb.create_sheet(SHEET_CLASSES)
    ws.append(["כיתה", "מחנכת"])
    ws.append(["א'1", "כהן רחל"])
    ws.append(["א'2", "לוי שרה"])
    _style(ws, [14, 24])

    ws = wb.create_sheet(SHEET_TEACHERS)
    ws.append(["מורה"])
    ws.append(["כהן רחל"])
    ws.append(["לוי שרה"])
    ws.append(["פרידמן חנה"])
    _style(ws, [24])

    ws = wb.create_sheet(SHEET_LESSONS)
    ws.append(["מקצוע", "כיתות", "מורות", "שעות בשבוע", "חדר", "שיעור סיוע"])
    ws.append(["תורה", "א'1", "כהן רחל", 5, "", ""])
    ws.append(["תורה", "א'2", "לוי שרה", 5, "", ""])
    ws.append(["התעמלות", "א'1, א'2", "פרידמן חנה", 2, "אולם", ""])
    _style(ws, [18, 24, 26, 14, 14, 12])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cells(ws):
    """שורות הלשונית, בלי שורות ריקות: (מספר שורה, [ערכים כטקסט])."""
    out = []
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        vals = ["" if v is None else str(v).strip() for v in row]
        if any(vals):
            out.append((i, vals))
    return out


def _split(text):
    return [x.strip() for x in re.split(r"[,،;]", text) if x.strip()]


def _norm_class(c):
    """מאחדת כתיבה של כיתה: א1 / א 1 / א'1 -> א'1"""
    m = re.fullmatch(r"([א-ת]+)\s*['׳’`]?\s*(\d+)", c.strip())
    return f"{m.group(1)}'{m.group(2)}" if m else c.strip()


def import_workbook(content: bytes):
    """בודקת קובץ אקסל. מחזירה (נתונים או None, שגיאות, אזהרות)."""
    errors, warnings = [], []
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        return None, ["לא הצלחתי לפתוח את הקובץ. צריך קובץ אקסל (xlsx)."], []
    for name in (SHEET_SETTINGS, SHEET_LESSONS):
        if name not in wb.sheetnames:
            errors.append(f"חסרה לשונית בשם '{name}'. כדאי להוריד את התבנית ולמלא אותה.")
    if errors:
        return None, errors, []

    # ---- הגדרות
    days, periods = [], []
    start, length = "08:00", 45
    for i, v in _cells(wb[SHEET_SETTINGS])[1:]:
        if v[0] in ALL_DAYS:
            try:
                n = int(float(v[1] or 0))
            except ValueError:
                errors.append(f"הגדרות, שורה {i}: מספר השיעורים של יום {v[0]} צריך להיות מספר.")
                continue
            if n > 0:
                days.append(v[0])
                periods.append(n)
        elif v[0].startswith("שעת התחלה"):
            if re.fullmatch(r"\d{1,2}:\d{2}", v[1] or ""):
                start = v[1]
            else:
                errors.append(f"הגדרות, שורה {i}: שעת ההתחלה צריכה להיות בפורמט 08:00.")
        elif v[0].startswith("אורך שיעור"):
            try:
                length = int(float(v[1]))
            except ValueError:
                errors.append(f"הגדרות, שורה {i}: אורך שיעור צריך להיות מספר דקות.")
    if not days:
        errors.append("בלשונית 'הגדרות' אין אף יום עם שיעורים.")
    # ימים שאינם ברצף (למשל בלי רביעי) לא נתמכים כרגע: נדרוש רצף מראשון
    if days and days != ALL_DAYS[:len(days)]:
        errors.append("הימים צריכים להיות ברצף, החל מיום ראשון (למשל ראשון עד חמישי).")

    # ---- שיעורים
    items, classes_seen, teachers_seen = [], [], []
    rows = _cells(wb[SHEET_LESSONS])[1:]
    if not rows:
        errors.append("בלשונית 'שיעורים' אין שורות.")
    for i, v in rows:
        v += [""] * (6 - len(v))
        subject, cls_txt, t_txt, hours_txt, room, pull = v[:6]
        where = f"שיעורים, שורה {i}"
        classes = [_norm_class(c) for c in _split(cls_txt)]
        teachers = _split(t_txt)
        if not subject:
            errors.append(f"{where}: חסר שם מקצוע.")
        if not classes:
            errors.append(f"{where}: חסרה כיתה.")
        if not teachers:
            errors.append(f"{where}: חסרה מורה.")
        try:
            hours = int(float(hours_txt))
            if hours < 1:
                raise ValueError
        except ValueError:
            errors.append(f"{where}: 'שעות בשבוע' צריך להיות מספר שלם, 1 ומעלה.")
            continue
        if days and hours > sum(periods):
            errors.append(f"{where}: {hours} שעות בשבוע, אבל בשבוע יש רק {sum(periods)} שיעורים.")
        item = {"subject": subject, "classes": classes, "teachers": teachers, "hours": hours}
        if room:
            item["room"] = room
        if pull.strip() in ("כן", "yes", "Yes", "1", "V", "v"):
            item["pullout"] = True
        items.append(item)
        for c in classes:
            if c not in classes_seen:
                classes_seen.append(c)
        for t in teachers:
            if t not in teachers_seen:
                teachers_seen.append(t)

    # כפילות: אותו מקצוע פעמיים באותה כיתה
    seen = {}
    for it in items:
        for c in it["classes"]:
            if (c, it["subject"]) in seen:
                errors.append(f"המקצוע '{it['subject']}' מופיע יותר מפעם אחת בכיתה {c}. אפשר לאחד לשורה אחת, או לשנות את השם של אחד מהם.")
            seen[(c, it["subject"])] = 1

    # ---- כיתות ומחנכות
    homeroom = {}
    if SHEET_CLASSES in wb.sheetnames:
        for i, v in _cells(wb[SHEET_CLASSES])[1:]:
            c = _norm_class(v[0])
            if c not in classes_seen:
                warnings.append(f"כיתות, שורה {i}: לכיתה {c} אין אף שיעור בלשונית 'שיעורים'. התעלמתי ממנה.")
                continue
            if len(v) > 1 and v[1]:
                homeroom[c] = v[1]
                if v[1] not in teachers_seen:
                    teachers_seen.append(v[1])
    classes = sorted(classes_seen, key=lambda c: (D.GRADES_ORDER.index(re.sub(r"[\s\d]+$", "", c)) if re.sub(r"[\s\d]+$", "", c) in D.GRADES_ORDER else 99, c))

    # ---- מורות
    if SHEET_TEACHERS in wb.sheetnames:
        for i, v in _cells(wb[SHEET_TEACHERS])[1:]:
            if v[0] and v[0] not in teachers_seen:
                teachers_seen.append(v[0])
                warnings.append(f"מורות, שורה {i}: למורה {v[0]} אין שיעורים. הוספתי אותה בלי שעות.")

    if errors:
        return None, errors, warnings

    # זמני שיעורים: רצף, בלי הפסקות
    h, m = map(int, start.split(":"))
    times, t = [], h * 60 + m
    for _ in range(max(periods)):
        times.append((f"{t // 60:02d}:{t % 60:02d}", f"{(t + length) // 60:02d}:{(t + length) % 60:02d}"))
        t += length
    rooms = {}
    for it in items:
        if it.get("room"):
            rooms.setdefault(it["room"], 1)
    raw = {
        "classes": classes, "homeroom": homeroom, "teachers": teachers_seen, "items": items,
        "settings": {"days": days, "periods": periods, "times": times, "rooms": rooms},
    }
    return raw, [], warnings


def save_custom(raw):
    D.CUSTOM_FILE.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")


def clear_custom():
    if D.CUSTOM_FILE.exists():
        D.CUSTOM_FILE.unlink()
