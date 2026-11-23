"""
יוצר ב-LangSmith את המאגר "mishbetzet-notes" מתוך examples.py.
מריצים פעם אחת (מתיקיית backend):

    .venv\\Scripts\\python -m evals.create_dataset
"""

from langsmith import Client

from app import llm  # noqa: F401  (טוען את backend/.env: מפתחות LangSmith ו-OpenAI)
from .examples import EXAMPLES

DATASET_NAME = "mishbetzet-notes"


def main():
    client = Client()
    if client.has_dataset(dataset_name=DATASET_NAME):
        print(f"המאגר '{DATASET_NAME}' כבר קיים. מוחקים אותו באתר LangSmith אם רוצים ליצור מחדש.")
        return
    client.create_dataset(DATASET_NAME, description="הערות חופשיות והכלל הצפוי מכל אחת")
    client.create_examples(
        dataset_name=DATASET_NAME,
        inputs=[{"text": text} for text, _ in EXAMPLES],
        outputs=[expected for _, expected in EXAMPLES],
    )
    print(f"נוצר המאגר '{DATASET_NAME}' עם {len(EXAMPLES)} דוגמאות.")


if __name__ == "__main__":
    main()
