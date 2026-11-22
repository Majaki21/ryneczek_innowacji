"""Search the filtered catalog with SQLite FTS5 and rank the matching records."""
import re
import unicodedata

STOP_WORDS = set(
    "a aby albo ale by co czy dla do i jak jest lub ma na nad o od oraz po pod przez "
    "przy sie sa to w we z za ze sposob jakim".split()
)
WORD = re.compile(r"[^\W_]+")
SUFFIXES = ("owego", "owymi", "owych", "ami", "ach", "owie", "emu", "ego",
            "owej", "om", "ow", "em", "ie", "y", "a", "u", "e", "i", "o")
CONCEPTS = (
    ("halas", "wycisz", "tlumien", "tlumik", "wytlum"),
    ("tor", "kolej", "szyn"),
    ("samochod", "motoryzac", "pojazd", "auto"),
    ("przedszkol", "przedszkolak"),
    ("oszczed", "redukc", "ogranicz", "zmniejsz"),
)


def normalize(text):
    return "".join(
        char for char in unicodedata.normalize("NFD", text.casefold().replace("ł", "l"))
        if not unicodedata.combining(char)
    )


def stem(word):
    for ending in SUFFIXES:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def prefix_root(root):
    return len(root) >= 3 and not root.isdigit()


def patterns(query):
    terms = dict.fromkeys(
        word for word in WORD.findall(normalize(query))
        if len(word) > 1 and word not in STOP_WORDS
    )
    groups = {}
    for word in terms:
        root = stem(word)
        variants = next(
            (group for group in CONCEPTS if any(root.startswith(value) for value in group)),
            (root,),
        )
        groups.setdefault(variants, set()).add(word)
    fts = set()
    for roots, exact in groups.items():
        fts.update(f'"{word}"' for word in exact)
        fts.update(f'"{root}"' + ("*" if prefix_root(root) else "") for root in roots)
    return " OR ".join(sorted(fts)), [
        (
            re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(exact))) + r")\b"),
            re.compile(r"\b(?:" + "|".join(
                re.escape(root) + (r"[^\W_]{0,10}" if prefix_root(root) else "")
                for root in roots
            ) + r")\b"),
        )
        for roots, exact in groups.items()
    ]


def build_lookup(db):
    db.execute("""
        CREATE VIRTUAL TABLE project_words USING fts5(
            terms, content='', detail=none, tokenize='unicode61'
        )
    """)
    db.executemany("INSERT INTO project_words(rowid, terms) VALUES (?, ?)", (
        (project_id, " ".join(WORD.findall(normalize(" ".join((title, summary, details, evidence))))))
        for project_id, title, summary, details, evidence in db.execute(
            "SELECT id,title,summary,business_details,coalesce(deployment_note,'') FROM projects"
        )
    ))
    db.execute("INSERT INTO project_words(project_words) VALUES ('optimize')")


def rank(db, query, where, params, *, indexed=True):
    lookup, groups = patterns(query)
    if not groups:
        raise ValueError("Wpisz przynajmniej jedno słowo opisujące projekt.")

    full = []
    partial = []
    minimum = max(1, (len(groups) + 1) // 2)
    if indexed and db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='project_words'"
    ).fetchone():
        where += (" AND " if where else " WHERE ") + """
            p.id IN (SELECT rowid FROM project_words WHERE project_words MATCH ?)
        """
        params = [*params, lookup]
    for project_id, title, summary, details, evidence in db.execute(
        "SELECT id,title,summary,business_details,coalesce(deployment_note,'') FROM projects p" + where, params
    ):
        title = normalize(title)
        description = normalize(summary)
        business = normalize(details)
        documented_use = normalize(evidence)
        score = 0
        matched = 0
        for exact, broad in groups:
            weight = (
                8 if exact.search(title) else
                6 if broad.search(title) else
                4 if exact.search(description) else
                3 if broad.search(description) else
                2 if exact.search(business) else
                1 if broad.search(business) else
                2 if exact.search(documented_use) else
                1 if broad.search(documented_use) else 0
            )
            score += weight + (2 if broad.search(documented_use) and broad.search(description) else 0)
            matched += bool(weight)
        if matched == len(groups):
            full.append((-score, project_id))
        elif matched >= minimum:
            partial.append((-matched, -score, project_id))

    results = [(project_id, "słowa lub ich odmiany", None) for _, project_id in sorted(full)]
    if len(results) < 3:
        results.extend(
            (project_id, "częściowe dopasowanie słów", None)
            for _, _, project_id in sorted(partial)[:3 - len(results)]
        )
    return results
