import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL")

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS innovations (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES profiles(id),
        title TEXT NOT NULL, summary TEXT NOT NULL, details TEXT NOT NULL,
        tags TEXT NOT NULL, stage TEXT NOT NULL, source TEXT UNIQUE,
        evidence TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS links (
        innovation TEXT NOT NULL REFERENCES innovations(id),
        profile TEXT NOT NULL REFERENCES profiles(id),
        role TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (innovation, profile, role)
    )""",
    """CREATE TABLE IF NOT EXISTS card_facts (
        innovation TEXT PRIMARY KEY REFERENCES innovations(id),
        facts TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS needs (
        id TEXT PRIMARY KEY, profile TEXT NOT NULL REFERENCES profiles(id),
        title TEXT NOT NULL, tag TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS need_facts (
        need TEXT PRIMARY KEY REFERENCES needs(id),
        description TEXT NOT NULL, available_conditions TEXT NOT NULL,
        shared INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS pilots (
        id TEXT PRIMARY KEY, need TEXT NOT NULL REFERENCES needs(id),
        innovation TEXT NOT NULL REFERENCES innovations(id),
        recipient TEXT NOT NULL REFERENCES profiles(id),
        UNIQUE (need, innovation)
    )""",
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY, innovation TEXT NOT NULL REFERENCES innovations(id),
        first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        phone TEXT NOT NULL, email TEXT NOT NULL,
        trl INTEGER NOT NULL, area TEXT NOT NULL, scope TEXT NOT NULL,
        repository TEXT NOT NULL, usage TEXT NOT NULL,
        attachments_note TEXT NOT NULL, created TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS project_files (
        id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
        name TEXT NOT NULL, content_type TEXT NOT NULL, size INTEGER NOT NULL,
        path TEXT NOT NULL
    )""",
)

PROFILES = [
    ("pci", "Recenzent PCI", "Zespół oceny"),
    ("uczelnia", "Zespół HydroLab", "Innowator"),
    ("gmina", "Gmina demonstracyjna", "Instytucja"),
    ("szkola", "Szkoła demonstracyjna", "Instytucja"),
    ("miasto", "Miasto demonstracyjne", "Instytucja"),
]


@contextmanager
def database():
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row
        connection = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    else:
        connection = sqlite3.connect(os.getenv("RADAR_SQLITE", "radar.sqlite3"))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

    def execute(query, params=()):
        return connection.execute(query.replace("?", "%s") if DATABASE_URL else query, params)

    try:
        with connection:
            yield execute
    finally:
        connection.close()


def initialize():
    with database() as run:
        for statement in SCHEMA:
            run(statement)
        for profile in PROFILES:
            run("INSERT INTO profiles VALUES (?, ?, ?) ON CONFLICT DO NOTHING", profile)

        for item in json.loads(Path("sources/catalog.json").read_text(encoding="utf-8")):
            inserted = run("""INSERT INTO innovations
                (id, owner, title, summary, details, tags, stage, source, evidence, published)
                VALUES (?, 'pci', ?, ?, '', ?, ?, ?, ?, 1) ON CONFLICT DO NOTHING""",
                (item["id"], item["title"], item["summary"], json.dumps(item["tags"]),
                 item["stage"], f"https://example.org/radar-demo/{item['id']}", item["evidence"]))
            if inserted.rowcount:
                store_facts(run, item["id"], item)
                for field, role in (("creator", "twórca"), ("adopter", "wdrażający")):
                    if item.get(field):
                        run("INSERT INTO links VALUES (?, ?, ?, 1)", (item["id"], item[field], role))


FACT_DEFAULTS = {
    "problem_evidence": "", "conditions": "", "condition_tags": [],
    "recipient": "", "metric": "", "provenance": "",
}


def store_facts(run, key, data):
    facts = {field: data.get(field, default) for field, default in FACT_DEFAULTS.items()}
    run("INSERT INTO card_facts VALUES (?, ?) ON CONFLICT DO NOTHING", (key, json.dumps(facts)))
