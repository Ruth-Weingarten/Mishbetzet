"""
מודל השפה: שלוש משימות.
1. translate_note  - הערה חופשית -> כלל מהרשימה (או "אין כלל מתאים")
2. interpret       - הודעת צ'אט של המנהלת -> פעולה מוגדרת
3. explain         - ניסוח הסבר קצר לחריגה

אם מוגדר OPENAI_API_KEY - משתמשים ב-OpenAI עם פלט מובנה (Pydantic).
אם לא - "מצב הדגמה": מפענח פשוט מבוסס מילות מפתח, כדי שהאתר יעבוד גם בלי מפתח.
המפענח הפשוט מוגבל בכוונה. כשהוא לא בטוח, הוא אומר "לא הבנתי" ולא מנחש.
"""

import os
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from . import data as D

# תעודות אבטחה: פייתון ישתמש בתעודות שווינדוס כבר סומך עליהן.
# בלי זה, סינון אינטרנט או אנטי-וירוס שבודקים תעבורה מאובטחת גורמים לשגיאת
# CERTIFICATE_VERIFY_FAILED בחיבור ל-OpenAI (ובהמשך גם ל-LangSmith).
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

def _load_env_file():
    """
    קורא את הקובץ backend/.env, אם קיים, ומכניס את הערכים שבו למשתני הסביבה.
    כך כותבים את המפתח פעם אחת בקובץ, ולא בכל הפעלה בטרמינל.
    (הקובץ לא עולה ל-GitHub: הוא רשום ב-.gitignore)
    """
    env = Path(__file__).resolve().parents[1] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_env_file()
USE_LLM = bool(os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

RULE_KINDS_DOC = """
סוגי הכללים האפשריים (kind) והפרמטרים שלהם:
- free_day: {teacher, day}  יום חופשי למורה
- teacher_not_periods: {teachers: [..], periods: [..], days?: [..]}  מורות לא בשעות מסוימות
- teacher_end_by: {teacher, day, last_period}  המורה מסיימת עד שעה מסוימת
- teacher_start_from: {teacher, day, first_period}  המורה מתחילה משעה מסוימת
- subject_days: {subject, days: [..]}  מקצוע רק בימים מסוימים
- no_double: {subject, grades?: [..]}  בלי שיעורים כפולים (אפשר רק בשכבות מסוימות, למשל ["א'", "ב'"])
- spread: {subject}  לא יותר משיעור אחד ביום
- teacher_gaps: {max_per_day, days?: [..], teachers?: [..]}  מקסימום חלונות ביום לכל מורה (אפשר רק בימים או למורות מסוימים)
- max_gaps_per_week: {max, teachers?: [..]}  מקסימום חלונות בשבוע (לכל המורות, או רק למורות מסוימות). מתאים גם ל"לא הגיוני שלמורה X יש N חלונות בשבוע"
- min_lessons_per_day: {min, teachers?: [..], days?: [..]}  מורה שמגיעה ביום מסוים תלמד בו לפחות min שיעורים (אפשר להגביל למורות או לימים מסוימים). מתאים גם ל"לא הגיוני שהמורה תבוא ליום X בשביל שיעור אחד"
- max_work_days: {threshold, above, below}  מספר ימי עבודה מקסימלי: למורה עם יותר מ-threshold שעות עד above ימים, לאחרות עד below
- short_day_early: {max_lessons, last_period}  מורה עם יום קצר (עד max_lessons שיעורים): השיעורים צמודים ומסתיימים עד last_period
כל הכללים על מורות מקבלים גם teachers: [שמות], וגם days: [ימים] כשצריך להגביל.
ימים: 0=ראשון ... 5=שישי. שעות: 0=שעה ראשונה (08:00) ... 6=שעה שביעית.
שעות השיעורים: 0: 8:00-8:45, 1: 8:45-9:30, 2: 9:45-10:30, 3: 10:30-11:15, 4: 11:30-12:15, 5: 12:15-13:00, 6: 13:00-13:45.
שמות המורות כתובים "משפחה פרטי". בהערה יכול להופיע רק שם המשפחה, או "פרטי משפחה": החזירי תמיד את השם המלא מהרשימה.
"""


# ---------- מבני הפלט (משותפים למודל ולמפענח הפשוט) ----------

class RuleProposal(BaseModel):
    matched: bool = Field(description="האם נמצא כלל מתאים מהרשימה")
    kind: Optional[str] = None
    params: dict = Field(default_factory=dict)
    summary: str = Field(description="משפט קצר בעברית: מה הבנת")


class Move(BaseModel):
    """הזזת שיעור מסוים למשבצת מסוימת."""
    cls: str = Field(description="שם הכיתה בדיוק כמו ברשימה, למשל ג'2")
    subject: str = Field(description="שם המקצוע בדיוק כמו ברשימה")
    day: int = Field(description="0=ראשון ... 5=שישי")
    period: int = Field(description="0=שעה ראשונה ... 6=שעה שביעית")


class ChatAction(BaseModel):
    type: Literal["decide", "add_rule", "move_lesson", "question", "approve", "unclear", "info", "rebuild"]
    conflict_id: Optional[str] = None
    option: Optional[str] = Field(None, description="waive=לוותר, alt_day=יום חלופי, show_alternatives=לאכוף (להראות דרכים)")
    rules: list[RuleProposal] = Field(default_factory=list,
                                      description="אם type=add_rule: כל הכללים החדשים שבהודעה, יחד")
    move: Optional[Move] = None
    question: Optional[str] = Field(None, description="שאלת הבהרה, אם type=unclear")
    reply: Optional[str] = Field(None, description="אם type=info: תשובה ישירה למנהלת, למשל שהכלל כבר קיים")
    unhandled: Optional[str] = Field(None, description="חלקים בהודעה שלא נכנסו לפעולה הזאת")
    summary: str = ""


# ---------- מפענח פשוט (מצב הדגמה) ----------

def _teachers_in(text):
    found = D.find_teachers(text)
    if "סגניות" in text or "הסגניות" in text:
        found += [t for t, v in D.TEACHERS.items() if v["role"] == "vice" and t not in found]
    return found


def _day_in(text):
    for i, d in enumerate(D.DAYS):
        if f"יום {d}" in text or f"ב{d}" in text or f"בימי {d}" in text or d in text.split():
            return i
    return None


def _hour_in(text):
    m = re.search(r"(?:עד|לפני|מ-?|מה?שעה)\s*(\d{1,2})(?::(\d{2}))?", text)
    if not m:
        return None
    h = int(m.group(1)) * 60 + int(m.group(2) or 0)
    return h


def _to_min(hhmm):
    h, mm = hhmm.split(":")
    return int(h) * 60 + int(mm)


def _fallback_rule(text) -> RuleProposal:
    teachers = _teachers_in(text)
    day = _day_in(text)
    minutes = _hour_in(text)
    if teachers and ("שעה ראשונה" in text or "בבוקר" in text and "לא" in text):
        return RuleProposal(matched=True, kind="teacher_not_periods",
                            params={"teachers": teachers, "periods": [0]},
                            summary=f"{', '.join(teachers)}: לא בשעה הראשונה, בכל הימים")
    if teachers and day is not None and ("חופש" in text):
        return RuleProposal(matched=True, kind="free_day", params={"teacher": teachers[0], "day": day},
                            summary=f"{teachers[0]}: יום {D.DAYS[day]} חופשי")
    if teachers and day is not None and minutes and ("עד" in text or "לסיים" in text):
        last = max([p for p, (_, end) in enumerate(D.PERIOD_TIMES) if _to_min(end) <= minutes], default=0)
        return RuleProposal(matched=True, kind="teacher_end_by",
                            params={"teacher": teachers[0], "day": day, "last_period": last},
                            summary=f"{teachers[0]}: ביום {D.DAYS[day]} לסיים עד {D.PERIOD_TIMES[last][1]}")
    if teachers and day is not None and minutes and ("לפני" in text or "להתחיל" in text):
        first = min([p for p, (st, _) in enumerate(D.PERIOD_TIMES) if _to_min(st) >= minutes], default=0)
        return RuleProposal(matched=True, kind="teacher_start_from",
                            params={"teacher": teachers[0], "day": day, "first_period": first},
                            summary=f"{teachers[0]}: ביום {D.DAYS[day]} להתחיל מ-{D.PERIOD_TIMES[first][0]}")
    return RuleProposal(matched=False, summary="לא נמצא כלל מתאים מהרשימה")


def _fallback_chat(text, conflicts) -> ChatAction:
    t = text.strip()
    if t in ("מאשרת", "אישור", "מאושר") or "מאשרת את המערכת" in t:
        return ChatAction(type="approve", summary="אישור סופי של המערכת")
    if "מחדש" in t and any(w in t for w in ("בנ", "הרצ", "תריצ", "שבצ")):
        return ChatAction(type="rebuild", summary="בנייה מחדש")
    if t.startswith("למה") or t.endswith("?"):
        return ChatAction(type="question", summary=t)
    rule = _fallback_rule(t)
    if rule.matched:
        return ChatAction(type="add_rule", rules=[rule], summary=rule.summary)
    if any(w in t for w in ("ותרי", "לוותר", "וותרי")):
        for c in conflicts:
            if any(name in t for name in _teachers_in(c["text"])) or c["id"] in t:
                return ChatAction(type="decide", conflict_id=c["id"], option="waive",
                                  summary=f"לוותר: {c['text']}")
    return ChatAction(type="unclear", question="לא הבנתי בדיוק. על איזו מורה או כיתה מדובר, ומה לשנות?")


# ---------- שרשראות (Chains) בתחביר LCEL ----------
# כל שרשרת = Prompt | Model | Parser. היא Runnable, ולכן מפעילים אותה עם invoke().
# השרשראות רצות בתוך צמתים של הגרף: "LCEL בתוך Nodes, ו-LangGraph לניהול התזרים".

def _model():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=MODEL, temperature=0)


def _build_chains():
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    vice = ", ".join(t for t, v in D.TEACHERS.items() if v["role"] == "vice")

    translate_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "את מתרגמת הערה של מנהלת בית ספר לכלל אחד מרשימה סגורה.\n{rules}\n"
         "שמות המורות: {teachers}. סגניות: {vice}.\n"
         "אם אין כלל מתאים, החזירי matched=false. אל תנחשי."),
        ("human", "ההערה: {text}"),
    ]).partial(rules=RULE_KINDS_DOC, teachers=", ".join(D.TEACHERS), vice=vice)

    interpret_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "את עוזרת למנהלת לבנות מערכת שעות. הפכי את ההודעה שלה לפעולה אחת.\n"
         "סוגים: decide (החלטה על חריגה קיימת: waive=לוותר, show_alternatives=לאכוף, alt_day=יום חלופי), "
         "add_rule (כללים חדשים), move_lesson (העברת שיעור), question (שאלה), approve (אישור סופי), "
         "unclear (לא ברור: נסחי שאלת הבהרה), info (תשובה ישירה בלי שינוי), "
         "rebuild (בקשה לבנות את המערכת מחדש לפי הכללים הנוכחיים: \"תבני מחדש\", \"תריצי שוב\"; בלי כללים חדשים).\n{rules}\n"
         "הכללים שכבר פעילים:\n{existing}\n"
         "החריגות הפתוחות:\n{conflicts}\n"
         "השיחה עד כה:\n{history}\n"
         "הנחיות:\n"
         "- הודעה יכולה להשלים את הקודמת (\"יש לה גם...\"). פרשי אותה לפי השיחה עד כה, ואל תשאלי שוב על מורה או כיתה שכבר הוזכרו.\n"
         "- דרישה לשנות משהו שקיים (\"תשני את זה\", \"לא הגיוני ש... תתקני\") היא add_rule, כשאפשר לנסח אותה כאחד מסוגי הכללים. למשל \"לא הגיוני שהמורה X תבוא ביום Y לשיעור אחד\" = min_lessons_per_day עם min=2, המורה והיום. רק אם אי אפשר, בקשי הבהרה בשאלה אחת קצרה.\n"
         "- אין צורך בניסוח מדויק. אם הבקשה לא תואמת בדיוק לסוג כלל, בחרי את הסוג הקרוב ביותר שמבצע את הכוונה (אפשר להגביל אותו למורה, ליום או לכיתה), וכתבי בתקציר מה הכלל יבצע בפועל. החזירי matched=false רק אם באמת אין סוג קרוב. כמעט כל כלל על מורה מקבל teachers, וכמעט כל כלל על ימים מקבל days.\n"
         "- הודעה שמתארת מצב קיים או מתלוננת עליו (\"למורה X יש שני חלונות\", \"לכיתה Y יש שיעור אחד\") "
         "היא question, לא add_rule ולא info. אל תגידי שכלל קיים מונע את זה: כלל רך יכול להיות מופר במערכת שנבנתה.\n"
         "- הודעה יכולה לכלול כמה בקשות. כל הכללים החדשים נכנסים יחד לרשימה rules.\n"
         "- חלק בהודעה שאינו מאותו סוג (למשל העברת שיעור יחד עם כללים) כתבי ב-unhandled. אל תשמיטי שום חלק בשקט.\n"
         "- אם בקשה כבר מכוסה בדיוק בכלל פעיל, אל תוסיפי אותה שוב. אם זו כל ההודעה: type=info, "
         "וב-reply הסבירי שהכלל כבר קיים ומה הוא אומר. בקשה שמחמירה כלל קיים היא כלל חדש.\n"
         "- 'חלון אחד למורה' או 'X חלונות למורה' בלי המילה 'ביום' = max_gaps_per_week.\n"
         "כיתות: {classes} (אפשר לכתוב גם בלי גרש: א1 = א'1). מורות: {teachers}. מקצועות: {subjects}.\n"
         "אם יש ספק, unclear עם שאלה. אל תנחשי."),
        ("human", "ההודעה: {text}"),
    ]).partial(rules=RULE_KINDS_DOC, classes=", ".join(D.CLASSES),
               teachers=", ".join(D.TEACHERS), subjects=", ".join(D.CURRICULUM))

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "את עוזרת למנהלת בית ספר להבין את מערכת השעות. עני בעברית פשוטה, בשניים-שלושה משפטים. "
         "עני רק לפי הנתונים שמצורפים. החלונות כבר מחושבים בנתונים: אל תחשבי אותם מחדש, "
         "ואם המנהלת צודקת, אמרי לה את זה ומה לא קוים. אם התשובה לא נמצאת בנתונים, אמרי שאין לך את המידע. אל תמציאי."),
        ("human", "השיחה עד כה:\n{history}\n\nהנתונים:\n{context}\n\nהשאלה: {question}"),
    ])

    explain_prompt = ChatPromptTemplate.from_template(
        "נסחי למנהלת בית ספר, בעברית פשוטה ובמשפט או שניים, למה הכלל הבא לא קוים "
        "ומה המשמעות. בלי מונחים טכניים.\n{base}")

    model = _model()
    return {
        # with_structured_output משמש כאן גם כ-Parser: הפלט הוא אובייקט Pydantic
        # function_calling: מתאים גם לשדות חופשיים כמו params
        "translate": translate_prompt | model.with_structured_output(RuleProposal, method="function_calling"),
        "interpret": interpret_prompt | model.with_structured_output(ChatAction, method="function_calling"),
        "explain": explain_prompt | model | StrOutputParser(),
        "answer": answer_prompt | model | StrOutputParser(),
    }


_CHAINS = None


def chains():
    global _CHAINS
    if _CHAINS is None:
        _CHAINS = _build_chains()
    return _CHAINS


# ---------- נפילה בטוחה ----------
# אם הקריאה למודל נכשלת (אין חיבור, אין קרדיט, מפתח שגוי), לא מפילים את כל הבנייה:
# משתמשים בגרסה הפשוטה של מצב ההדגמה, ומסמנים שהייתה תקלה כדי שהגרף יודיע למנהלת.

LLM_DOWN_MSG = "אין כרגע חיבור למודל השפה, אז אני עובדת במצב פשוט: אבין פחות טוב ניסוחים חופשיים."
_failed = False


def _safe(run, fallback):
    global _failed
    try:
        return run()
    except Exception as e:
        print(f"[משבצת] הקריאה למודל נכשלה, ממשיכה במצב הדגמה: {type(e).__name__}: {e}")
        _failed = True
        return fallback()


def take_failure() -> bool:
    """האם הייתה תקלה מאז הבדיקה הקודמת. הבדיקה גם מאפסת את הסימון."""
    global _failed
    failed, _failed = _failed, False
    return failed


# ---------- הפונקציות שהגרף קורא להן ----------

def translate_note(text: str) -> RuleProposal:
    if not USE_LLM:
        return _fallback_rule(text)
    return _safe(lambda: chains()["translate"].invoke({"text": text}),
                 lambda: _fallback_rule(text))


def interpret(text: str, conflicts: list, existing: list = (), history: str = "") -> ChatAction:
    if not USE_LLM:
        return _fallback_chat(text, conflicts)
    listed = "\n".join(f"- {c['id']}: {c['text']}" for c in conflicts) or "(אין)"
    rules = "\n".join(f"- {c['text']}" for c in existing) or "(אין)"
    return _safe(lambda: chains()["interpret"].invoke({"text": text, "conflicts": listed, "existing": rules,
                                                      "history": history or "(תחילת שיחה)"}),
                 lambda: _fallback_chat(text, conflicts))


def explain(conflict: dict) -> str:
    """הסבר קצר לחריגה. במצב הדגמה: תבנית קבועה."""
    n = len(conflict["instances"])
    where = ", ".join(i["label"] for i in conflict["instances"][:4])
    more = f" ועוד {n - 4}" if n > 4 else ""
    places = "במקום אחד" if n == 1 else f"ב־{n} מקומות"
    base = f"הכלל \"{conflict['text']}\" לא קוים {places}: {where}{more}."
    if not USE_LLM:
        return base
    return _safe(lambda: chains()["explain"].invoke({"base": base}), lambda: base)


def answer(question: str, context: str, history: str = "") -> Optional[str]:
    """עונה על שאלה לפי הנתונים בלבד. במצב הדגמה מחזיר None, והגרף משתמש בגרסה הפשוטה."""
    if not USE_LLM:
        return None
    return _safe(lambda: chains()["answer"].invoke({"question": question, "context": context,
                                                    "history": history or "(תחילת שיחה)"}),
                 lambda: None)
