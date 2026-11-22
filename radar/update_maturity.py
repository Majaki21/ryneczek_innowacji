"""Add reproducible, unpublished-as-fact TRL estimates before serving the catalog."""
import re
import sqlite3
from pathlib import Path
from contextlib import closing

SIGNALS = [
    (7, 9, r"\b(?:wdrożono|wdrożyliśmy|wprowadzono na rynek|jest obecnie (?:stosowan[ayoe]|wykorzystywan[ayoe])|has been deployed|was deployed|in commercial use)\b"),
    (5, 7, r"\b(?:przeprowadzono pilotaż|przetestowano w warunkach (?:rzeczywistych|operacyjnych)|pilot was completed|tested in (?:the field|an operational environment))\b"),
    (3, 4, r"\b(?:przeprowadzono testy laboratoryjne|przetestowano w laboratorium|was (?:tested|validated) in (?:the |a )?lab)\b"),
    (3, 5, r"\b(?:zbudowano prototyp|wykonano prototyp|powstał prototyp|prototype was (?:built|developed))\b"),
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


THESIS = re.compile(
    r"\b(?:prac[ayę] (?:dyplomow\w*|licencjack\w*|magistersk\w*|inżyniersk\w*|doktorsk\w*)"
    r"|rozpraw[ayę] doktorsk\w*|doktorat|master.s thesis|doctoral thesis|phd thesis)\b", re.I
)
COMPANY = re.compile(
    r"^(?:Beneficjent|Wykonawca):[^\n]*(?:sp\.\s*z\s*o\.\s*o\.|spółka|"
    r"\bs\.\s*a\.|\bltd\b|\bgmbh\b|\bprzedsiębiorstwo\b)", re.I | re.M
)
ENGINEERING = re.compile(
    r"\b(?:prace rozwojowe|badania przemysłowe|projekt badawczo.rozwojowy|prototyp\w*|"
    r"linia pilotażowa|industrial research|experimental development)\b", re.I
)


def classify(title, summary, details, source, category, deployment):
    technical = category == "Technologia"
    signal = estimate(summary) if technical else None
    if signal:
        return (*signal, "estimate")
    if technical and deployment == "yes":
        return 7, 9, "Materiał źródłowy opisuje wdrożenie technologii.", "estimate"
    if THESIS.search(title) or THESIS.search(source):
        return 1, 3, "Profil pracy akademickiej. Opis nie podaje etapu walidacji technologii.", "profile"
    if COMPANY.search(details):
        return 3, 5, "Profil projektu realizowanego przez firmę. Opis nie podaje etapu walidacji technologii.", "profile"
    if ENGINEERING.search(title) or ENGINEERING.search(summary):
        return 3, 5, "Profil prac badawczo-rozwojowych lub prototypowania. Etap walidacji nie został ustalony.", "profile"
    if technical:
        return 2, 4, "Profil projektu technologicznego. Opis nie podaje etapu walidacji.", "profile"
    return 1, 3, "Domyślny zakres dla opisu bez danych o gotowości technologii. W projektach nietechnicznych TRL ma ograniczone zastosowanie.", "profile"


def update(path):
    with closing(sqlite3.connect(path)) as db, db:
        rows = db.execute("""
            SELECT id,title,summary,business_details,source,category,deployment
            FROM projects WHERE trl_min IS NULL OR trl_basis='profile'
        """).fetchall()
        db.executemany("""UPDATE projects SET trl_min=?,trl_max=?,trl_evidence=?,trl_basis=?
                       WHERE id=?""", ((*classify(*fields), project_id) for project_id, *fields in rows))
        print(db.execute("SELECT trl_basis,count(*) FROM projects GROUP BY trl_basis").fetchall())


if __name__ == "__main__":
    update(Path("sources/search.sqlite"))
