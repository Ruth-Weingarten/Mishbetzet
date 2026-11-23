# שיעורים: הקוד של משבצת לפי חומר הקורס

כל שיעור בנוי כך: קודם הרעיון, אחר כך הקוד האמיתי מהפרויקט, ובסוף שאלות הבנה. השיעורים הולכים לפי הסדר של מצגות הקורס.

---

## שיעור 0: שרשרת (Chain)
מבוסס על מצגת LangChain, שקפים 4 עד 9.

**שלוש אבני הבניין:**
- **תבנית הנחיה:** טקסט עם "חורים" שממלאים.
- **המודל:** מקבל את ההנחיה ומחזיר תשובה.
- **מפענח הפלט:** הופך את התשובה למבנה שהקוד יכול להשתמש בו.

**החיבור ביניהם:** מחברים אותן עם `|`, והפלט של כל שלב הוא הקלט של השלב הבא:
```python
chain = prompt | model | parser
chain.invoke({...})
```

**אצלנו:**
```
backend/app/llm.py
```
```python
"translate": translate_prompt | model.with_structured_output(RuleProposal)
"explain":   explain_prompt | model | StrOutputParser()
```

**למה שרשרת לא מספיקה לנו:** שרשרת היא צינור קבוע. היא לא יודעת להתפצל, לחזור אחורה או לעצור ולחכות לאדם. לכן השרשראות רצות **בתוך הצמתים**, והגרף מנהל את התהליך כולו.

**שאלות:**
1. מה נכנס לתבנית ההנחיה, ומה יוצא מהמפענח בסוף?
2. למה חשוב שהשרשרת מחזירה אובייקט עם שדות ולא משפט חופשי?
3. איזו בעיה מונעת ההוראה "אם אין כלל מתאים, החזירי matched=false. אל תנחשי"?

---

## שיעור 1: גרף, מצב, צמתים וקשתות
מבוסס על מצגת LangChain, שקפים 10 עד 14, ועל מצגת LangGraph, מפגש 1.

**מצב:** "דף" משותף שעובר בין הצמתים.
```python
class TimetableState(TypedDict, total=False):
    constraints: list[dict]
    result: dict
    conflicts: list[dict]
    chat: Annotated[list[dict], operator.add]   # Reducer: מצטבר, לא נדרס
    round: int
```

**צומת:** פונקציה שמחזירה רק את מה שהשתנה.
```python
def solve(state):
    result = solver.solve(state["constraints"], ...)
    return {"result": result, "round": state["round"] + 1}
```

**קשתות:** קשת רגילה, וקשת מותנה.
```python
g.add_edge("load_data", "translate_notes")
g.add_conditional_edges("solve", route_after_solve, ["diagnose", "explain", "await_principal"])
g.add_edge("apply_decision", "solve")      # הקשת הזאת יוצרת את הלולאה
```

**שאלות:**
1. כש־`solve` מחזיר רק את `result` ואת `round`, מה קורה לשאר השדות במצב?
2. מה ההבדל בין השדה `chat`, שיש לו את `operator.add`, לבין `result`, שאין לו?
3. למה `route_after_solve` היא פונקציה נפרדת ולא חלק מ־`solve`?

---

## שיעור 2 (הבא): עצירה לאישור אדם ושמירת מצב
`interrupt()`, `Command(resume=...)`, שמירת מצב (checkpointer) ו־`thread_id`. מבוסס על שקפים 15 ו־16.
