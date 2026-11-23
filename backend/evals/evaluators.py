"""
מעריכים (Evaluators): קוד קטן שנותן ציון לתשובה של המודל.

שני ציונים לכל דוגמה:
  matched_correct - האם המודל צדק בשאלה "יש כלל מתאים או אין"
  rule_correct    - האם הכלל כולו נכון: סוג, מורות, ימים ושעות
"""


def canon(matched, kind, params):
    """הופך כלל (כמו שהמערכת שומרת אותו) לצורה אחידה להשוואה."""
    params = params or {}
    if not matched:
        return {"matched": False, "kind": None, "teachers": [], "days": [], "periods": []}
    teachers = params.get("teachers") or ([params["teacher"]] if params.get("teacher") else [])
    days = params.get("days") or ([params["day"]] if params.get("day") is not None else [])
    periods = params.get("periods")
    if periods is None:
        if params.get("last_period") is not None:
            periods = [params["last_period"]]
        elif params.get("first_period") is not None:
            periods = [params["first_period"]]
        else:
            periods = []
    return {"matched": True, "kind": kind, "teachers": sorted(teachers),
            "days": sorted(days), "periods": sorted(periods)}


def matched_correct(outputs: dict, reference_outputs: dict) -> dict:
    ok = bool(outputs.get("matched")) == bool(reference_outputs.get("matched"))
    return {"key": "matched_correct", "score": 1 if ok else 0}


def rule_correct(outputs: dict, reference_outputs: dict) -> dict:
    fields = ("matched", "kind", "teachers", "days", "periods")
    ok = all(outputs.get(f) == reference_outputs.get(f) for f in fields)
    return {"key": "rule_correct", "score": 1 if ok else 0}
