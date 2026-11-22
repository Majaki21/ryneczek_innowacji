"""Add reproducible, unpublished-as-fact TRL estimates before serving the catalog."""
import re
import sqlite3
from pathlib import Path
from contextlib import closing

SIGNALS = [
    (7, 9, r"\b(?:wdrożono|wdrożyliśmy|wprowadzono na rynek|jest obecnie (?:stosowan[ayoe]|wykorzystywan[ayoe])|has been deployed|was deployed|in commercial use)\b"),
    (5, 7, r"\b(?:przeprowadzono pilotaż|przetestowano w warunkach (?:rzeczywistych|operacyjnych)|pilot was completed|tested in (?:the field|an operational environment))\b"),
    (3, 4, r"\b(?:przeprowadzono testy laboratoryjne|przetestowano w laboratorium|was (?:tested|validated) in (?:the |a )?lab)\b"),
    (3, 6, r"\b(?:zbudowano prototyp|wykonano prototyp|powstał prototyp|prototype was (?:built|developed))\b"),
    (2, 3, r"\b(?:opracowano koncepcję technologii|sformułowano koncepcję technologiczną|technology concept was formulated)\b"),
]
FUTURE_OR_NEGATED = re.compile(r"\b(?:nie|not|never|planuj\w*|będzie|będą|will|aims?|expected)\b", re.I)
RULES = [(low, high, re.compile(pattern, re.I)) for low, high, pattern in SIGNALS]


def estimate(text):
    sentences = re.split(r"(?<=[.!?])\s+|\n", text)
    for low, high, pattern in RULES:
        for sentence in sentences:
            hit = pattern.search(sentence)
            if hit and not FUTURE_OR_NEGATED.search(sentence):
                return low, high, sentence.strip()[:320]
    return None


def update(path):
    with closing(sqlite3.connect(path)) as db, db:
        changes = []
        for project_id, summary in db.execute(
            "SELECT id,summary FROM projects WHERE trl_min IS NULL AND category='Technologia'"
        ):
            result = estimate(summary)
            if result:
                changes.append((*result, project_id))
        db.executemany("""UPDATE projects SET trl_min=?,trl_max=?,trl_evidence=?,trl_basis='estimate'
                       WHERE id=?""", changes)
        print(f"Dodano {len(changes)} zakresów szacunkowych TRL.")


if __name__ == "__main__":
    update(Path("sources/search.sqlite"))
