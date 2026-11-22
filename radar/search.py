"""Read-only search and filters for the public project catalog."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/catalog")
PHRASE_LOCK = Lock()
CARD_FIELDS = "id,title,summary,business_details,url,source,category,trl,COALESCE(deployment_stage,deployment) AS deployment,page_url,page_specific,trl_min,trl_max,trl_basis"
SOURCE_DIR = Path(__file__).resolve().parents[1] / "sources"
UNKNOWN = "unknown"
Filters = Annotated[list[str] | None, Query(max_length=40)]


def connect():
    path = Path(os.getenv("RADAR_SEARCH_DB", str(SOURCE_DIR / "search.sqlite"))).resolve()
    try:
        database = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise HTTPException(503, "Nie udało się otworzyć bazy katalogu.") from exc
    database.row_factory = sqlite3.Row
    return database


def get_rules():
    return json.loads((SOURCE_DIR / "catalog-filters.json").read_text(encoding="utf-8"))


@router.get("/filters")
def filters():
    rules = get_rules()
    with closing(connect()) as db:
        trl_available = bool(db.execute("SELECT 1 FROM projects WHERE trl_min IS NOT NULL LIMIT 1").fetchone())
    return {
        "categories": {key: list(values) for key, values in rules["kategorie"].items()},
        "technologies": list(rules["technologie"]),
        "places": list(rules["miejsca"]),
        "trl_available": trl_available,
    }


def facet(kind, values):
    placeholders = ",".join("?" for _ in values)
    return (
        f"p.id IN (SELECT project FROM facets WHERE kind=? AND value IN ({placeholders}))",
        [kind, *values],
    )


def categories_filter(categories, subcategories):
    family = get_rules()["kategorie"]
    unknown = set(categories) - set(family)
    unknown_subcategories = set(subcategories) - {label for members in family.values() for label in members}
    if unknown or unknown_subcategories:
        raise HTTPException(422, "Nieznana kategoria lub podkategoria.")
    branches = []
    params = []
    for label, members in family.items():
        selected = [value for value in subcategories if value in members]
        if label not in categories and not selected:
            continue
        parts = ["p.category=?"]
        params.append(label)
        if selected:
            clause, values = facet("subcategory", selected)
            parts.append(clause)
            params.extend(values)
        branches.append("(" + " AND ".join(parts) + ")")
    return "(" + " OR ".join(branches) + ")", params


def enum_filter(expression, values):
    conditions = []
    params = []
    for value in dict.fromkeys(values):
        if value == UNKNOWN:
            conditions.append(f"{expression} IS NULL")
        else:
            conditions.append(f"{expression}=?")
            params.append(value)
    return "(" + " OR ".join(conditions) + ")", params


def item(row):
    return dict(row)


def build_where(category, subcategory, technology, place, trl, deployment, skip=None):
    conditions = []
    params = []
    if "category" != skip and (category or subcategory):
        clause, values = categories_filter(category or [], subcategory or [])
        conditions.append(clause)
        params.extend(values)
    for kind, selected in (("technology", technology), ("place", place)):
        if selected and kind != skip:
            clause, values = facet(kind, selected)
            conditions.append(clause)
            params.extend(values)
    if trl and skip != "trl":
        if any(value not in {UNKNOWN, *map(str, range(1, 10))} for value in trl):
            raise HTTPException(422, "Wybierz TRL od 1 do 9 lub Brak danych.")
        alternatives = []
        for value in dict.fromkeys(trl):
            if value == UNKNOWN:
                alternatives.append("p.trl_min IS NULL")
            else:
                alternatives.append("? BETWEEN p.trl_min AND p.trl_max")
                params.append(int(value))
        conditions.append("(" + " OR ".join(alternatives) + ")")
    if deployment and skip != "deployment":
        clause, values = enum_filter("COALESCE(p.deployment_stage,p.deployment)", deployment)
        conditions.append(clause)
        params.extend(values)
    return (" WHERE " + " AND ".join(conditions) if conditions else ""), params


def available_filters(db, category, subcategory, technology, place, trl, deployment):
    availability = {}
    for kind in ("category", "technology", "place", "trl", "deployment"):
        where, params = build_where(category, subcategory, technology, place, trl, deployment, skip=kind)
        if kind == "trl":
            values = set()
            for low, high in db.execute("SELECT DISTINCT p.trl_min,p.trl_max FROM projects p" + where, params):
                values.update([UNKNOWN] if low is None else map(str, range(low, high + 1)))
            availability[kind] = sorted(values)
        if kind in ("category", "deployment"):
            expression = "COALESCE(p.deployment_stage,p.deployment)" if kind == "deployment" else "p.category"
            rows = db.execute(f"SELECT DISTINCT {expression} FROM projects p" + where, params)
            availability[kind] = [str(row[0]) if row[0] is not None else UNKNOWN for row in rows]
        if kind in ("category", "technology", "place"):
            facet_kind = "subcategory" if kind == "category" else kind
            rows = db.execute(
                "SELECT DISTINCT f.value FROM facets f JOIN projects p ON p.id=f.project "
                + (" WHERE " if not where else where + " AND ") + "f.kind=?",
                [*params, facet_kind],
            )
            availability[facet_kind] = [row[0] for row in rows]
    return availability


@router.get("")
def catalog(
    q: Annotated[str, Query(max_length=500)] = "",
    category: Filters = None,
    subcategory: Filters = None,
    technology: Filters = None,
    place: Filters = None,
    trl: Filters = None,
    deployment: Annotated[list[Literal["yes", "no", "unknown", "in_progress", "potential", "research"]] | None, Query(max_length=6)] = None,
    availability: bool = False,
    page: Annotated[int, Query(ge=1, le=5000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=60)] = 18,
):
    where, params = build_where(category, subcategory, technology, place, trl, deployment)
    q = q.strip()
    offset = (page - 1) * page_size
    with closing(connect()) as db:
        if q:
            try:
                if os.getenv("RADAR_PHRASE_MODE") == "e5":
                    with PHRASE_LOCK:
                        from .phrase import rank
                        matches = rank(q, where, params)
                else:
                    from .words import rank
                    matches = rank(db, q, where, params)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            except (ImportError, sqlite3.OperationalError) as exc:
                raise HTTPException(503, "Uruchom Przygotuj-Wyszukiwanie.cmd, aby przygotować wyszukiwanie fraz.") from exc
            total = len(matches)
            items = []
            for project_id, match, _ in matches[offset:offset + page_size]:
                row = db.execute(f"SELECT {CARD_FIELDS} FROM projects WHERE id=?", (project_id,)).fetchone()
                items.append({**item(row), "match": match})
        else:
            total = db.execute("SELECT count(*) FROM projects p" + where, params).fetchone()[0]
            rows = db.execute(f"SELECT {CARD_FIELDS} FROM projects p" + where + """
                ORDER BY CASE WHEN COALESCE(deployment_stage,deployment)='yes' THEN 0 ELSE 1 END, title COLLATE NOCASE, id
                LIMIT ? OFFSET ?
            """, (*params, page_size, offset))
            items = [item(row) for row in rows]
        options = available_filters(db, category, subcategory, technology, place, trl, deployment) if availability else None
    return {"available": options, "items": items, "total": total, "page": page, "page_size": page_size,
            "q": q, "phrase_matching": bool(q)}


@router.get("/{project_id}")
def detail(project_id: int):
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Nie znaleziono projektu.")
        data = item(row)
        data["deployment"] = data["deployment_stage"] or data["deployment"]
        evidence_sources = db.execute(
            "SELECT label,url FROM project_review_sources WHERE project_id=? ORDER BY label", (project_id,)
        ).fetchall()
        data["review_sources"] = [item(source) for source in evidence_sources]
        fragments = db.execute(
            "SELECT source_url,fragments FROM project_source_fragments WHERE project_id=?", (project_id,)
        ).fetchone()
        data["source_fragments"] = (
            {"url": fragments["source_url"], "items": json.loads(fragments["fragments"])}
            if fragments else None
        )
        labels = db.execute("SELECT kind,value FROM facets WHERE project=? ORDER BY value", (project_id,)).fetchall()
        related = db.execute("""SELECT id,title,source,url,page_url,page_specific FROM projects
                                WHERE group_id=? AND id<>? ORDER BY title, id""",
                             (data["group_id"], project_id)).fetchall()
        documents = db.execute(
            "SELECT title,source,url,kind FROM related_documents WHERE group_id=? ORDER BY title",
            (data["group_id"],),
        ).fetchall()
    data["facets"] = {kind: [value for label, value in labels if label == kind]
                      for kind in ("subcategory", "technology", "place")}
    data["organizations"] = json.loads(data["organizations"])
    data["places_evidence"] = json.loads(data["places_evidence"] or "[]")
    data["related"] = [item(x) for x in (*related, *documents)]
    return data
