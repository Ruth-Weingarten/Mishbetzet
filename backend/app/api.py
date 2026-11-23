"""
השרת: מחבר בין הממשק לבין הגרף.

הרעיון המרכזי: כל "ריצה" של בניית מערכת היא thread בגרף.
- POST /api/runs               -> מתחיל ריצה חדשה, הגרף רץ עד העצירה הראשונה
- POST /api/runs/{id}/resume   -> מעביר את תשובת המנהלת, הגרף ממשיך עד העצירה הבאה
- GET  /api/runs/{id}          -> המצב הנוכחי: המערכת, החריגות, היומן, ומה הגרף מחכה לו
"""

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from . import data as D
from . import llm
from .graph import graph, teacher_graph

app = FastAPI(title="משבצת")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

RUNS: set[str] = set()


def _cfg(run_id):
    return {"configurable": {"thread_id": run_id}, "recursion_limit": 100}


def snapshot(run_id: str):
    """המצב של הריצה, בפורמט שהממשק צריך."""
    st = graph.get_state(_cfg(run_id))
    v = st.values
    waiting = [i.value for t in st.tasks for i in t.interrupts]
    result = v.get("result") or {}
    return {
        "id": run_id,
        "waiting": waiting[0] if waiting else None,
        "round": v.get("round", 0),
        "published": v.get("published", False),
        "lessons": result.get("lessons", []),
        "conflicts": v.get("conflicts", []) if waiting and waiting[0]["type"] == "decision" else [],
        "chat": v.get("chat", []),
        "constraints": v.get("constraints", []),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.USE_LLM}


@app.get("/api/school")
def school():
    return {**D.school_snapshot(), "llm": llm.USE_LLM}


@app.post("/api/runs")
def start_run():
    run_id = uuid.uuid4().hex[:8]
    RUNS.add(run_id)
    graph.invoke({}, _cfg(run_id))
    return snapshot(run_id)


class Resume(BaseModel):
    value: Any


@app.post("/api/runs/{run_id}/resume")
def resume(run_id: str, body: Resume):
    if run_id not in RUNS:
        raise HTTPException(404, "הריצה לא נמצאה (השרת אותחל מחדש?)")
    graph.invoke(Command(resume=body.value), _cfg(run_id))
    return snapshot(run_id)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(404, "הריצה לא נמצאה")
    return snapshot(run_id)


# ---------- כללי בית הספר: ביטול ועריכה ----------

class RulePatch(BaseModel):
    enabled: bool | None = None
    text: str | None = None
    params: dict[str, int] | None = None


@app.put("/api/rules/{rule_id}")
def patch_rule(rule_id: str, body: RulePatch):
    """ביטול כלל (או הפעלה מחדש), ועריכת הניסוח והמספרים שלו. חל מהבנייה הבאה."""
    rule = next((r for r in D.SCHOOL_RULES if r["id"] == rule_id), None)
    if rule is None:
        raise HTTPException(404, "הכלל לא נמצא")
    if body.enabled is not None:
        rule["enabled"] = body.enabled
    if body.text is not None and body.text.strip():
        rule["text"] = body.text.strip()
    for key, value in (body.params or {}).items():
        current = rule["params"].get(key)
        if isinstance(current, int) and not isinstance(current, bool):   # רק מספרים קיימים
            rule["params"][key] = value
    return rule


# ---------- טופס המורה: גרף קטן עם אישור של המורה ----------

class TeacherText(BaseModel):
    teacher: str
    text: str


@app.post("/api/teacher/translate")
def teacher_translate(body: TeacherText):
    tid = uuid.uuid4().hex[:8]
    cfg = {"configurable": {"thread_id": tid}}
    teacher_graph.invoke({"teacher": body.teacher, "text": body.text}, cfg)
    st = teacher_graph.get_state(cfg)
    waiting = [i.value for t in st.tasks for i in t.interrupts]
    return {"thread": tid, "proposal": st.values["proposal"], "waiting": waiting[0] if waiting else None}


class TeacherConfirm(BaseModel):
    ok: bool


@app.post("/api/teacher/{tid}/confirm")
def teacher_confirm(tid: str, body: TeacherConfirm):
    cfg = {"configurable": {"thread_id": tid}}
    teacher_graph.invoke(Command(resume=body.ok), cfg)
    v = teacher_graph.get_state(cfg).values
    if v.get("confirmed"):
        # שומרים את התרגום שהמורה אישרה בטופס שלה
        form = D.FORMS.setdefault(v["teacher"], D._form(submitted=False))
        form["free_text"] = v["text"]
        form["confirmed_rule"] = v["proposal"]
    return {"confirmed": v.get("confirmed")}


# ---------- טפסים: המורה שומרת, המנהלת רואה הכול ----------

class FormBody(BaseModel):
    free_day: str | None = None
    alt_day: str | None = None
    subjects: list[str] = []
    blocked_class: str | None = None
    reason: str = ""
    leave: bool = False
    leave_when: str = ""
    reduce_hours: int = 0
    free_text: str = ""


@app.get("/api/forms")
def all_forms():
    """למנהלת: כל המורות, ומה כל אחת ביקשה (כולל הסיבות, שרק המנהלת רואה)."""
    return [{"teacher": t, "hours": D.teacher_hours()[t], "form": D.FORMS.get(t)} for t in D.TEACHERS]


@app.get("/api/forms/{teacher}")
def my_form(teacher: str):
    if teacher not in D.TEACHERS:
        raise HTTPException(404, "מורה לא נמצאה")
    return D.FORMS.get(teacher) or D._form(submitted=False)


@app.put("/api/forms/{teacher}")
def save_form(teacher: str, body: FormBody):
    if teacher not in D.TEACHERS:
        raise HTTPException(404, "מורה לא נמצאה")
    old = D.FORMS.get(teacher) or {}
    form = D._form(**body.model_dump())
    # תרגום שאושר נשמר רק אם הטקסט לא השתנה
    if old.get("free_text") == body.free_text:
        form["confirmed_rule"] = old.get("confirmed_rule")
    D.FORMS[teacher] = form
    return form


# ---------- הגשת הממשק הבנוי ----------

DIST = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(DIST / "index.html")
