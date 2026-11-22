"""Extract supporting fragments from archived primary project pages."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sqlite3

RULES = {
    "Wdrożenie lub komercjalizacja": re.compile(
        r"\b(?:wdrożono|wdrożyliśmy|zosta\w+ wdrożon\w+|wprowadzono na rynek|"
        r"wdrożon\w+ do produkcji|jest stosowan\w+|sprzedajemy|has been deployed)\b", re.I),
    "Test, pilotaż lub prototyp": re.compile(
        r"\b(?:przeprowadzono (?:testy|pilotaż|badania|próby)|przetestowano|"
        r"wyniki (?:badań|testów|pilotażu)|zbudowano prototyp|opracowano prototyp|"
        r"wykonano (?:testy|próby|prototyp)|testy (?:laboratoryjne|terenowe)|"
        r"pilotaż odbył się|w ramach pilotażu|was tested|tests showed)\b", re.I),
    "Technika lub sposób użycia": re.compile(
        r"\b(?:wykorzyst\w+|polega|opiera się|składa się|umożliwia|"
        r"stosuje się|zaprojektowano|opracowano|przeznaczon\w+|"
        r"do pomiaru|do analizy|za pomocą|automatyczn\w+|program\w+|"
        r"system\w+|technolog\w+|rozwiązani\w+|metod\w+|narzędzi\w+)\b", re.I),
}
FUTURE = re.compile(r"\b(?:nie|not|może|mogą|miałyby|mógłby|planuj\w*|planowan\w*|będzie|będą|docelowo|"
                    r"zakłada\w*|will|expected|w przyszłości|możliwość wdrożenia)\b", re.I)
BOILERPLATE = re.compile(r"nasza rada dla innych|pliki do pobrania|więcej informacji w regulaminie|"
                         r"pliki cookie|stopka|zapisz się|opowiedz nam krótko|"
                         r"strona główna|sprawdź jak załatwić|skontaktuj się z nami",re.I)
SPLIT = re.compile(r"(?<!\bsp\.)(?<!\bdr\.)(?<!\bnp\.)(?<!\bm\.in\.)(?<=[.!?])\s+|\n")
START = re.compile(r"jakiego problemu|jaki problem|zobacz efekt|o innowacji|jak wdrożyć",re.I)
END = re.compile(r"nasza rada dla innych|opowiedz nam krótko|pliki do pobrania",re.I)


def fragments(body):
    lines = body.splitlines()
    useful = [i for i,line in enumerate(lines) if len(line)<110 and START.search(line)]
    start = useful[-1] if len(useful)>3 else useful[0] if useful else 0
    end = next((i for i in range(start+1,len(lines)) if len(lines[i])<95 and END.search(lines[i])),len(lines))
    hits = defaultdict(list)
    for sentence in SPLIT.split("\n".join(lines[start:end])):
        text = " ".join(sentence.split()).strip(" –-•")
        if not 75 <= len(text) <= 800 or text.endswith("?") or BOILERPLATE.search(text):
            continue
        if re.search(r"https?://|[{}]|@|\b(?:tel|telefon|e-mail|NIP|REGON|PESEL)\b",text,re.I):
            continue
        for key, pattern in RULES.items():
            if not pattern.search(text):
                continue
            if key != "Technika lub sposób użycia" and FUTURE.search(text):
                continue
            hits[key].append(text)
            break
    result=[]
    for key, choices in hits.items():
        text=max(choices,key=lambda sentence: min(len(sentence),235)-max(0,len(sentence)-280)*.9)
        if len(text)>270:
            text=text[:269].rsplit(" ",1)[0]+"…"
        result.append([key,text])
    priority = list(RULES)
    return sorted(result,key=lambda f:priority.index(f[0]))[:2]


def generate(raw, catalog, destination, limit):
    excluded = {url for url, in catalog.execute(
        "SELECT DISTINCT p.url FROM projects p JOIN project_review_sources s ON s.project_id=p.id"
    )}
    keys = set(catalog.execute("SELECT source,source_id FROM projects"))
    results=[]
    counts=Counter()
    for source, key, body, url in raw.execute("""
        SELECT zrodlo,identyfikator,opis,link FROM rekordy
        WHERE zrodlo IN ('NCBR','Innowacje Społeczne','RAD-on – projekty') AND length(opis)>=1000
        ORDER BY CASE zrodlo WHEN 'NCBR' THEN 0 WHEN 'Innowacje Społeczne' THEN 1 ELSE 2 END, identyfikator
    """):
        if url in excluded or (source,key) not in keys:
            continue
        evidence=fragments(body)
        if evidence:
            results.append([source,key,url,evidence])
            counts[source]+=1
        if len(results)==limit:
            break
    if len(results)!=limit:
        raise ValueError(f"Zebrano {len(results)} kart, oczekiwano {limit}.")
    destination.mkdir(parents=True,exist_ok=True)
    for start in range(0,len(results),50):
        (destination/f"{start//50+1:02d}.json").write_text(
            json.dumps(results[start:start+50],ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(counts)
    print(Counter(k for *_,items in results for k,_ in items))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("raw")
    parser.add_argument("catalog")
    args=parser.parse_args()
    with sqlite3.connect(args.raw) as raw, sqlite3.connect(args.catalog) as catalog:
        generate(raw,catalog,Path("sources/review500"),500)
