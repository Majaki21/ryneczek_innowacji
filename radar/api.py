import base64
import binascii
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl

from radar.assessment import assessment
from radar.db import FACT_DEFAULTS, database, initialize, store_facts
from radar.matching import need_matches, similar
from radar.search import router as catalog_router

Stage = Literal["pomysł", "prototyp", "pilotaż", "wdrożenie", "nieustalony"]
Role = Literal["twórca", "wdrażający"]
ShortText = Annotated[str, Field(min_length=1, max_length=200, pattern=r"\S")]
PUBLIC = "id, title, summary, tags, stage, source, evidence, facts"
REVIEW_SCOPE = """owner = ? OR ? = 'pci' OR id IN (
    SELECT innovation FROM links WHERE profile = ?
)"""
INSTITUTIONS = {"gmina", "szkola", "miasto"}
NEEDS = """SELECT needs.*, description, available_conditions, shared
           FROM needs LEFT JOIN need_facts ON needs.id = need_facts.need"""
UPLOADS = Path(os.getenv("RADAR_UPLOADS", "uploads"))
MIN_TRL = 3
MAX_FILES = 5
MAX_FILE_BYTES = 8 * 1024 * 1024
AREAS = (
    "Środowisko i klimat", "Energia", "Mobilność i transport", "Zdrowie", "Edukacja",
    "Przemysł i produkcja", "Rolnictwo i żywność", "Administracja i smart city",
    "Społeczeństwo i kultura", "Cyfryzacja i IT", "Inne",
)
SCOPES = ("lokalny", "regionalny", "krajowy", "międzynarodowy")
TRL_LABELS = {
    1: "zaobserwowano podstawowe zasady", 2: "sformułowano koncepcję technologii",
    3: "eksperymentalne potwierdzenie koncepcji", 4: "walidacja w warunkach laboratoryjnych",
    5: "walidacja w środowisku zbliżonym do rzeczywistego",
    6: "demonstracja w środowisku zbliżonym do rzeczywistego",
    7: "demonstracja prototypu w środowisku operacyjnym", 8: "system ukończony i zakwalifikowany",
    9: "system sprawdzony w środowisku operacyjnym",
}
TRL_TOO_LOW = (
    "Jeszcze chwila pracy! Projekty przyjmujemy od poziomu TRL 3, czyli od eksperymentalnego "
    "potwierdzenia koncepcji. Dopracuj pomysł i wróć do nas, gdy będzie gotowy. Trzymamy kciuki!"
)


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")

app.include_router(catalog_router)

class Facts(BaseModel):
    problem_evidence: str = Field(default="", max_length=1500)
    conditions: str = Field(default="", max_length=1500)
    condition_tags: list[ShortText] = Field(default_factory=list, max_length=12)
    recipient: str = Field(default="", max_length=200)
    metric: str = Field(default="", max_length=500)


class Draft(Facts):
    title: ShortText
    summary: Annotated[str, Field(min_length=1, max_length=1500, pattern=r"\S")]
    tags: list[ShortText] = Field(default_factory=list, max_length=12)
    stage: Stage = "nieustalony"


class Submission(Draft):
    details: str = Field(default="", max_length=5000)
    evidence: str = Field(default="", max_length=4000)


class Candidate(Draft):
    source: HttpUrl
    evidence: str = Field(max_length=4000)
    creator: Literal["uczelnia"] | None = None
    adopter: Literal["gmina"] | None = None
    provenance: Literal["feed", "bielik"] = "feed"


class Need(BaseModel):
    title: ShortText
    tag: ShortText
    description: str = Field(default="", max_length=1500)
    available_conditions: list[ShortText] = Field(default_factory=list, max_length=12)
    shared: bool = False


class Attachment(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: str = Field(default="application/octet-stream", max_length=200)
    data: str = Field(max_length=MAX_FILE_BYTES * 4 // 3 + 16)


class Project(BaseModel):
    first_name: ShortText
    last_name: ShortText
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=200)
    title: ShortText
    description: Annotated[str, Field(min_length=1, max_length=1500, pattern=r"\S")]
    attachments_note: str = Field(default="", max_length=1500)
    files: list[Attachment] = Field(default_factory=list)
    trl: int
    area: str
    scope: str
    repository: str = Field(max_length=500)
    usage: str = Field(default="", max_length=1500)


def actor(x_demo_token: Annotated[str, Header()] = ""):
    for profile in ("pci", "uczelnia", "gmina", "szkola", "miasto"):
        if compare_digest(x_demo_token.encode(), f"{profile}-demo".encode()):
            return profile
    raise HTTPException(401, "Podaj klucz profilu demonstracyjnego")


Actor = Annotated[str, Depends(actor)]


def read_item(row):
    item = dict(row)
    item["tags"] = json.loads(item["tags"])
    facts = item.pop("facts")
    item.update(FACT_DEFAULTS)
    item.update(json.loads(facts) if facts else {})
    item["demo"] = bool(item["source"] and item["source"].startswith("https://example.org/radar-demo/"))
    item["source_status"] = (
        "Fikcyjne dane demonstracyjne" if item["demo"]
        else "Materiał publiczny · niezależna weryfikacja oczekuje" if item["source"]
        else "Deklaracja zgłaszającego"
    )
    return item


def card_links(run, key, confirmed_only=False):
    confirmed = "AND confirmed = 1" if confirmed_only else ""
    return [dict(link) for link in run(f"""
        SELECT profile, role, confirmed, name FROM links JOIN profiles ON profile = id
        WHERE innovation = ? {confirmed} ORDER BY name, role
    """, (key,))]


def public_items(run, query="", params=()):
    items = [
        read_item(row) for row in run(f"""
            SELECT {PUBLIC} FROM innovations LEFT JOIN card_facts ON id = innovation
            WHERE published = 1 {query} ORDER BY title
        """, params)
    ]
    for item in items:
        item["links"] = card_links(run, item["id"], confirmed_only=True)
        item["assessment"] = assessment(item, item["links"])
    return items


def read_need(row):
    item = dict(row)
    item["description"] = item["description"] or ""
    item["available_conditions"] = json.loads(item["available_conditions"] or "[]")
    item["shared"] = bool(item["shared"])
    return item


@app.get("/api/health")
def health():
    with database() as run:
        run("SELECT 1").fetchone()
    return {"status": "ok"}


@app.get("/api/discovery")
def discovery(tag: str = "", q: str = "", stage: Stage | Literal[""] = ""):
    with database() as run:
        items = public_items(run)
    return [
        item for item in items
        if (not tag or tag.casefold() in map(str.casefold, item["tags"]))
        and (not stage or item["stage"] == stage)
        and q.strip().casefold() in " ".join([item["title"], item["summary"], *item["tags"]]).casefold()
    ]


@app.get("/api/innovations/{key}")
def innovation(key: str):
    with database() as run:
        catalog = public_items(run)
    for item in catalog:
        if item["id"] == key:
            return {**item, "similar": similar(item, catalog)}
    raise HTTPException(404, "Brak opublikowanej karty")


@app.get("/api/review")
def review(profile: Actor):
    with database() as run:
        result = []
        for row in run(
            f"""SELECT innovations.*, facts FROM innovations LEFT JOIN card_facts ON id = innovation
                WHERE {REVIEW_SCOPE} ORDER BY title""", (profile, profile, profile)
        ).fetchall():
            item = read_item(row)
            if profile not in (item["owner"], "pci"):
                item.pop("details")
            item["links"] = card_links(run, item["id"])
            item["assessment"] = assessment(item, item["links"])
            result.append(item)
        return result


@app.post("/api/submissions", status_code=201)
def submit(draft: Submission, profile: Actor):
    key = str(uuid4())
    with database() as run:
        run("""INSERT INTO innovations
            (id, owner, title, summary, details, tags, stage, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, profile, draft.title, draft.summary, draft.details, json.dumps(draft.tags), draft.stage, draft.evidence))
        store_facts(run, key, draft.model_dump())
        run("INSERT INTO links VALUES (?, ?, 'twórca', 1)", (key, profile))
    return {"id": key}


def trl_stage(trl):
    return "prototyp" if trl <= 4 else "pilotaż" if trl <= 7 else "wdrożenie"


def check_project(project):
    if not 1 <= project.trl <= 9:
        raise HTTPException(422, "Wybierz stopień TRL od 1 do 9.")
    if project.trl < MIN_TRL:
        raise HTTPException(422, TRL_TOO_LOW)
    if project.area not in AREAS:
        raise HTTPException(422, "Wybierz obszar oddziaływania z listy.")
    if project.scope not in SCOPES:
        raise HTTPException(422, "Wybierz zasięg oddziaływania z listy.")
    phone, email = project.phone.strip(), project.email.strip()
    if not phone and not email:
        raise HTTPException(422, "Podaj telefon lub adres e-mail, abyśmy mogli się skontaktować.")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Adres e-mail wygląda na niepełny. Sprawdź go, proszę.")
    if phone and not re.fullmatch(r"\+?[\d\s()-]{7,20}", phone):
        raise HTTPException(422, "Numer telefonu może zawierać tylko cyfry, spacje, nawiasy, myślniki i znak +.")
    repo = project.repository.strip()
    if not repo:
        raise HTTPException(422, "Dodaj link do repozytorium GIT, artykułu lub innego potwierdzenia. Potrzebujemy go do weryfikacji.")
    if not re.fullmatch(r"https?://\S+", repo):
        raise HTTPException(422, "Link powinien zaczynać się od http:// lub https://.")
    if len(project.files) > MAX_FILES:
        raise HTTPException(422, f"Możesz dołączyć maksymalnie {MAX_FILES} plików.")
    decoded = []
    for attachment in project.files:
        try:
            content = base64.b64decode(attachment.data, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(422, f"Nie udało się odczytać pliku {attachment.name}.")
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(422, f"Plik {attachment.name} przekracza 8 MB.")
        decoded.append((attachment, content))
    return decoded


@app.post("/api/projects", status_code=201)
def add_project(project: Project):
    files = check_project(project)
    key, card = str(uuid4()), str(uuid4())
    contact = " · ".join(value for value in (project.phone.strip(), project.email.strip()) if value)
    details = "\n".join(line for line in (
        f"Zgłaszający: {project.first_name} {project.last_name}",
        f"Kontakt: {contact}",
        f"TRL {project.trl}: {TRL_LABELS[project.trl]}",
        f"Obszar oddziaływania: {project.area} · zasięg {project.scope}",
        f"Potwierdzenie (repozytorium/artykuł): {project.repository.strip()}",
        f"Opis załączników: {project.attachments_note.strip()}" if project.attachments_note.strip() else "",
        f"Załączniki: {', '.join(a.name for a, _ in files)}" if files else "",
    ) if line)
    folder = UPLOADS / key
    with database() as run:
        run("""INSERT INTO innovations
            (id, owner, title, summary, details, tags, stage, evidence)
            VALUES (?, 'pci', ?, ?, ?, ?, ?, ?)""",
            (card, project.title, project.description, details,
             json.dumps([project.area.casefold(), project.scope]), trl_stage(project.trl), project.usage))
        store_facts(run, card, {})
        run("""INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, card, project.first_name, project.last_name, project.phone.strip(), project.email.strip(),
             project.trl, project.area, project.scope, project.repository.strip(), project.usage,
             project.attachments_note, datetime.now(timezone.utc).isoformat()))
        if files:
            folder.mkdir(parents=True, exist_ok=True)
        for attachment, content in files:
            file_id = str(uuid4())
            safe = re.sub(r"[^\w.\-]+", "_", Path(attachment.name).name)[:120] or "plik"
            path = folder / f"{file_id}-{safe}"
            path.write_bytes(content)
            run("INSERT INTO project_files VALUES (?, ?, ?, ?, ?, ?)",
                (file_id, key, attachment.name, attachment.content_type, len(content), str(path)))
    return {"id": key, "card": card, "stage": trl_stage(project.trl)}


@app.post("/api/import")
def import_candidate(candidate: Candidate, x_import_token: Annotated[str, Header()] = ""):
    expected = os.getenv("RADAR_IMPORT_TOKEN", "import-demo")
    if not compare_digest(x_import_token.encode(), expected.encode()):
        raise HTTPException(401, "Nieprawidłowy klucz importu")
    key = str(uuid4())
    with database() as run:
        inserted = run("""INSERT INTO innovations
            (id, owner, title, summary, details, tags, stage, source, evidence)
            VALUES (?, 'pci', ?, ?, '', ?, ?, ?, ?) ON CONFLICT (source) DO NOTHING""",
            (key, candidate.title, candidate.summary, json.dumps(candidate.tags), candidate.stage,
             str(candidate.source), candidate.evidence))
        if not inserted.rowcount:
            return {"created": False}
        store_facts(run, key, candidate.model_dump())
        for profile, role in ((candidate.creator, "twórca"), (candidate.adopter, "wdrażający")):
            if profile:
                run("INSERT INTO links VALUES (?, ?, ?, 0)", (key, profile, role))
    return {"created": True, "id": key}


def visible_card(run, key, profile):
    card = run(
        f"SELECT owner, published FROM innovations WHERE id = ? AND (published = 1 OR {REVIEW_SCOPE})",
        (key, profile, profile, profile),
    ).fetchone()
    if card is None:
        raise HTTPException(404, "Brak innowacji")
    return card


@app.post("/api/innovations/{key}/links/{role}")
def link(key: str, role: Role, profile: Actor):
    with database() as run:
        visible_card(run, key, profile)
        existing = run("""SELECT 1 FROM links WHERE innovation = ? AND profile = ? AND role = ?""",
                       (key, profile, role)).fetchone()
        if not existing:
            raise HTTPException(403, "Brak propozycji powiązania dla tego profilu")
        run("UPDATE links SET confirmed = 1 WHERE innovation = ? AND profile = ? AND role = ?",
            (key, profile, role))
    return {"confirmed": True}


@app.post("/api/innovations/{key}/publish")
def publish(key: str, profile: Actor):
    with database() as run:
        item = visible_card(run, key, profile)
        if item["owner"] != profile:
            raise HTTPException(403, "Publikacja wymaga zgody właściciela karty")
        if not item["published"]:
            if run("SELECT 1 FROM links WHERE innovation = ? AND confirmed = 0", (key,)).fetchone():
                raise HTTPException(409, "Najpierw potwierdź wszystkie przypisane role")
            run("UPDATE innovations SET published = 1 WHERE id = ?", (key,))
    return {"published": True}


@app.post("/api/needs", status_code=201)
def add_need(need: Need, profile: Actor):
    if profile not in INSTITUTIONS:
        raise HTTPException(403, "Zgłoszenie potrzeby jest dostępne dla profilu instytucji")
    tag = need.tag.strip()
    with database() as run:
        key = str(uuid4())
        run("INSERT INTO needs VALUES (?, ?, ?, ?)", (key, profile, need.title, tag))
        run("INSERT INTO need_facts VALUES (?, ?, ?, ?)",
            (key, need.description, json.dumps(need.available_conditions), int(need.shared)))
    return {"id": key}


@app.get("/api/needs")
def needs(profile: Actor):
    with database() as run:
        items = public_items(run)
        return [
            {**need, "matches": need_matches(need, items, profile)}
            for need in map(read_need, run(f"{NEEDS} WHERE profile = ? ORDER BY title", (profile,)))
        ]


@app.post("/api/needs/{need_id}/pilots/{key}", status_code=201)
def request_pilot(need_id: str, key: str, profile: Actor):
    with database() as run:
        row = run(f"{NEEDS} WHERE needs.id = ? AND profile = ?", (need_id, profile)).fetchone()
        if row is None:
            raise HTTPException(404, "Brak potrzeby w tym profilu")
        matches = need_matches(read_need(row), public_items(run, "AND id = ?", (key,)), profile)
        if not matches or not matches[0]["pilot_recipient"]:
            raise HTTPException(409, "Brak dopasowania z potwierdzonym odbiorcą pilotażu")
        recipient = matches[0]["pilot_recipient"]["profile"]
        run("""INSERT INTO pilots VALUES (?, ?, ?, ?)
               ON CONFLICT (need, innovation) DO NOTHING""", (str(uuid4()), need_id, key, recipient))
        return dict(run("SELECT * FROM pilots WHERE need = ? AND innovation = ?", (need_id, key)).fetchone())


@app.get("/api/pilots")
def pilots(profile: Actor):
    with database() as run:
        return [dict(row) for row in run("""
            SELECT pilots.*, innovations.title AS innovation_title,
                   needs.title AS need_title, needs.profile AS requester,
                   sender.name AS requester_name, recipient.name AS recipient_name
            FROM pilots
            JOIN needs ON pilots.need = needs.id
            JOIN innovations ON pilots.innovation = innovations.id
            JOIN profiles AS sender ON sender.id = needs.profile
            JOIN profiles AS recipient ON recipient.id = pilots.recipient
            WHERE needs.profile = ? OR pilots.recipient = ?
            ORDER BY innovation_title, need_title
        """, (profile, profile))]


if Path("web").is_dir():
    app.mount("/", StaticFiles(directory="web", html=True))
