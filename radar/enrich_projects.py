"""Apply source-reviewed project facts and precise catalog classification rules."""
from contextlib import closing
from pathlib import Path
import json
import re
import sqlite3

from .words import build_lookup
from . import reviews_november

NCBR = "https://www.gov.pl/web/ncbr/"
CHEMICAL = "Technologie chemiczne"
MATERIALS = "Materiały i technologie produkcji"
PHOTONICS = "Elektronika i fotonika"
ZEUS = "opracowanie-bionicznej-protezy-przedramienia-zeus-o-modulowej-konstrukcji-odznaczajacej-sie-wysoka-wytrzymaloscia-na-uderzenia-i-intuicyjnej-kontroli-ruchu-opartej-na-przetwarzaniu-biosygnalow"
ALK = "akademia-360---zintegrowany-system-podnoszenia-jakosci-w-alk"
REVIEWS = {
    "projekt-br-laven": (
        "yes", ("Informatyka i telekomunikacja",),
        "Laven opracował narzędzie do kalkulacji składek i parametrów produktów ubezpieczeniowych. Projekt objął również dostosowanie algorytmów do dystrybucji produktów przez banki.",
        "Karta NCBR opisuje użycie narzędzia przez spółkę przy kalkulacji składek we współpracy z towarzystwami ubezpieczeniowymi i brokerami.",
        (("NCBR – opis narzędzia i jego wykorzystania", NCBR+"projekt-br-laven"),),
    ),
    ZEUS: (
        "yes", ("Technologie medyczne i biotechnologia",),
        "Zeus to modułowa proteza dłoni sterowana sygnałami elektrycznymi mięśni. Mechanizm obejmuje niezależnie poruszające się palce i kciuk do różnych chwytów.",
        "W relacji NCBR producent opisuje sprzedaż do klinik i warsztatów protetycznych. Aether Biomedical udostępnia dokumentację użytkową urządzenia.",
        (("NCBR – rozwój protezy i sprzedaż", NCBR + ZEUS),
         ("Aether Biomedical – instrukcja urządzenia", "https://www.aetherbiomedical.com/hubfs/IFU_Zeus%20T_V6.0_EN_20250328-Jun-18-2025-05-48-57-8265-AM.pdf?hsLang=en")),
    ),
    ALK: (
        "yes", ("Edukacja akademicka", "Kształcenie zawodowe i staże"),
        "Akademia Leona Koźmińskiego uruchomiła programy studiów związane z analizą danych, AI w zarządzaniu i rozwojem przedsiębiorstw. Projekt objął również doradztwo zawodowe KARIERA+ oraz system obsługi studentów oparty na Salesforce.",
        "W relacji NCBR uczelnia podaje, że w trakcie projektu z doradztwa skorzystało 811 studentów, a 290 osób ukończyło płatne staże.",
        (("NCBR – wyniki projektu Akademia 360", NCBR + ALK),),
    ),
    "petra": (
        "yes", (CHEMICAL, PHOTONICS),
        "Analizator wykorzystuje spektroskopię w podczerwieni, aby rozpoznawać substancje. VIGO opracowało hermetyczny moduł detekcyjny LWIR o paśmie 1 GHz ze zintegrowaną elektroniką. W urządzeniu analizującym moduł współpracuje z kaskadowym laserem kwantowym.",
        "Wykonano serię pilotażową modułów. Pomiar rozrzutu parametrów pozwolił poprawić powtarzalność montażu, zwiększyć pasmo i ograniczyć szum. NCBR opisuje wdrożenie modułu do produkcji oraz jego użycie w urządzeniu dostępnym komercyjnie.",
        (("NCBR – opis serii pilotażowej i komercjalizacji", NCBR+"petra"),
         ("VIGO Photonics – dokumentacja projektów Eurostars", "https://vigophotonics.com/pl/o-nas/projekty-badawcze/eurostars/")),
    ),
    "aerosize": (
        "yes", (MATERIALS,),
        "Hybrydowa kamizelka lawinowa wykorzystuje nabój gazowy do napełnienia szkieletu pneumatycznego. Większa część objętości poduszki wypełnia się zasysanym powietrzem, dzięki czemu system można nosić niezależnie od plecaka.",
        "Na karcie producenta można kupić Vest ONE. Producent podaje, że TÜV SÜD zbadał i certyfikował kamizelkę według EN 16716:2017.",
        (("NCBR – prototypy i próby w terenie", NCBR+"aerosize"),
         ("AEROSIZE – karta produktu", "https://aerosize.com/pl/produkt/aerosize-avalanche-airbag-vest-one/"),
         ("AEROSIZE – certyfikacja", "https://aerosize.com/declaration/")),
    ),
    "aktywny-koherentny-spektrometr-dyspersyjny": (
        "yes", (CHEMICAL, PHOTONICS),
        "Spektrometr ACCORDS służy do wykrywania niewielkich ilości gazów. W module VIGO struktura detekcyjna i przedwzmacniacz transimpedancyjny o paśmie około 1 GHz pracują w jednej hermetycznej obudowie.",
        "Zespół testował detektor i cały moduł optoelektroniczny. NCBR podaje, że moduł wszedł do produkcji i oferty VIGO. Mirico użyło detektorów VIGO i laserów Alpes Lasers w spektrometrze.",
        (("NCBR – testy i produkcja modułu", NCBR+"aktywny-koherentny-spektrometr-dyspersyjny"),
         ("VIGO – projekt ACCORDS", "https://vigo.com.pl/o-nas/projekty-badawcze/eurostars/accords/")),
    ),
    "cieplownia-przyszlosci-euros-energy-hc-plant": (
        "yes", ("Energetyka",),
        "Pełnoskalowy demonstrator w Lidzbarku Warmińskim łączy pompy ciepła, hybrydowe kolektory słoneczne i sezonowe magazynowanie ciepła. W instalacji pracuje m.in. wysokotemperaturowy magazyn wodny typu PTES.",
        "Według karty NCBR instalacja zasila w ciepło i ciepłą wodę budynki mieszkalne o łącznej powierzchni około 30 tys. m² na osiedlu Astronomów.",
        (("NCBR – instalacja i odbiorcy ciepła", NCBR+"cieplownia-przyszlosci-euros-energy-hc-plant"),),
    ),
    "metoda-natychmiastowego-wytwarzania-przyrostowego-czesci-zamiennych-i-alternatywnych-aparatury-medycznej": (
        "in_progress", (MATERIALS,),
        "Projekt opracował cyfrowy magazyn modeli części zamiennych do aparatury medycznej. Platforma gromadzi instrukcje i modele demonstratorów oraz wspiera koordynację rozproszonej produkcji przyrostowej.",
        "NCBR opisuje zastosowanie wytycznych jakościowych w międzynarodowej pilotażowej platformie cyfrowej. Status dotyczy tego pilotażu.",
        (("NCBR – demonstratory i platforma pilotażowa", NCBR+"metoda-natychmiastowego-wytwarzania-przyrostowego-czesci-zamiennych-i-alternatywnych-aparatury-medycznej"),),
    ),
    "zastosowanie-cieczy-nienewtonowskich-w-ukladach-absorbujacych-energie": (
        "yes", (MATERIALS,),
        "Badano ciecze nienewtonowskie pod kątem wykorzystania w konstrukcjach absorbujących energię uderzenia, m.in. w rozwiązaniach ochronnych.",
        "W opisie NCBR jako podmioty, które wdrożyły wyniki projektu, wskazano Smart Fluid i Gedeon.",
        (("NCBR – zakres badań i podmioty wdrażające", NCBR+"zastosowanie-cieczy-nienewtonowskich-w-ukladach-absorbujacych-energie"),),
    ),
    "toucan-eye": (
        "potential", ("Informatyka i telekomunikacja",),
        "Toucan Eye to przenośne urządzenie opracowywane z myślą o osobach z dysfunkcją wzroku. Projekt łączy kamerę i analizę obrazu z interfejsem przystosowanym do potrzeb osób niedowidzących.",
        "Strona zespołu opisuje urządzenie i współpracę z Polskim Związkiem Niewidomych. To wskazanie odbiorców i potencjalnego zastosowania.",
        (("Toucan Systems – opis rozwiązania", "https://ai.toucan-systems.pl/"),),
    ),
    "coolmen": (
        "in_progress", ("Technologie medyczne i biotechnologia",),
        "Urządzenie łączy nakładkę chłodzącą, czujniki, układ regulacji temperatury i aplikację mobilną do odczytu danych.",
        "Karta NCBR opisuje wdrażanie urządzenia przy udziale zespołów z Warszawskiego Uniwersytetu Medycznego i Wojskowego Instytutu Medycznego. To status z opisu projektu.",
        (("NCBR – opis urządzenia i etapu prac", NCBR+"coolmen"),),
    ),
}

CHEMICAL_TITLE = re.compile(
    r"\b(?:analizator\w* petrochemiczn\w*|reaktor\w* chemiczn\w*|"
    r"syntez\w* chemiczn\w*|technologi\w* chemiczn\w*|petrochemical analy[sz]er\w*)\b",
    re.I,
)


def add_facet(db, project_id, kind, value):
    db.execute("INSERT OR IGNORE INTO facets(project,kind,value) VALUES(?,?,?)", (project_id, kind, value))


def add_live_reviews(db):
    updates = 0
    for file in sorted(Path("sources/live-reviews").glob("*.json")):
        for url, stage, trl, summary, evidence, refs in json.loads(file.read_text(encoding="utf-8")):
            row = db.execute(
                "SELECT id FROM projects WHERE source='NCBR' AND source_id=? "
                "AND deployment IS NULL AND deployment_stage IS NULL", (url,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Brak karty bez statusu wdrożenia: {url}")
            project_id = row[0]
            db.execute("""
                UPDATE projects SET deployment_stage=?,summary=?,deployment_note=? WHERE id=?
            """, (stage, summary, evidence, project_id))
            if trl:
                db.execute("""
                    UPDATE projects SET trl_min=?,trl_max=?,trl_basis='estimate',trl_evidence=NULL
                    WHERE id=? AND (trl_basis IS NULL OR trl_basis!='declared')
                """, (*trl, project_id))
            db.executemany("INSERT INTO project_review_sources VALUES(?,?,?)",
                           ((project_id, title, source_url) for title, source_url in refs))
            updates += 1
    if updates != 89:
        raise ValueError(f"Oczekiwano 89 uzupełnień, otrzymano {updates}.")
    return updates


def enrich(db):
    db.execute("ALTER TABLE projects ADD COLUMN deployment_stage TEXT")
    db.executescript("""
        CREATE TABLE project_review_sources (
            project_id INTEGER NOT NULL, label TEXT NOT NULL, url TEXT NOT NULL,
            PRIMARY KEY (project_id, url)
        ) WITHOUT ROWID;
        CREATE INDEX project_deployment_stage ON projects(deployment_stage);
    """)
    rule_count = 0
    for project_id, title in db.execute("SELECT id,title FROM projects WHERE category IS NULL"):
        if CHEMICAL_TITLE.search(title):
            db.execute("UPDATE projects SET category='Technologia',classification_status='do sprawdzenia' WHERE id=?", (project_id,))
            add_facet(db, project_id, "subcategory", CHEMICAL)
            rule_count += 1
    reviewed_cards = REVIEWS | reviews_november.REVIEWS
    for slug, (stage, categories, summary, evidence, sources) in reviewed_cards.items():
        row = db.execute("SELECT id FROM projects WHERE source='NCBR' AND source_id=?", (NCBR + slug,)).fetchone()
        if row is None:
            raise ValueError(f"Brak rekordu NCBR: {slug}")
        project_id = row[0]
        db.execute("""
            UPDATE projects SET category=?, classification_status='zweryfikowana',
              summary=?, deployment=CASE WHEN ?='yes' THEN 'yes' ELSE deployment END,
              deployment_stage=?, deployment_note=?
            WHERE id=?
        """, (reviews_november.DOMAINS.get(slug, "Edukacja" if slug == ALK else "Technologia"),
               summary, stage, stage, evidence, project_id))
        if slug in reviews_november.TRL:
            db.execute("""
                UPDATE projects SET trl_min=?,trl_max=?,trl_basis='estimate',trl_evidence=NULL
                WHERE id=? AND (trl_basis IS NULL OR trl_basis!='declared')
            """, (*reviews_november.TRL[slug], project_id))
        for category in categories:
            add_facet(db, project_id, "subcategory", category)
        if slug == "toucan-eye":
            db.execute("UPDATE projects SET page_url=? WHERE id=?", (sources[0][1], project_id))
        db.executemany("INSERT INTO project_review_sources VALUES(?,?,?)",
                       ((project_id, label, url) for label, url in sources))
    db.execute("""
        CREATE TABLE project_source_fragments (
            project_id INTEGER PRIMARY KEY, source_url TEXT NOT NULL, fragments TEXT NOT NULL
        )
    """)
    reviewed = 0
    for file in sorted(Path("sources/review500").glob("*.json")):
        for source, source_id, source_url, fragments in json.loads(file.read_text(encoding="utf-8")):
            row = db.execute("SELECT id FROM projects WHERE source=? AND source_id=?",
                             (source, source_id)).fetchone()
            if row is None:
                raise ValueError(f"Nie znaleziono karty {source}: {source_id}")
            db.execute("INSERT INTO project_source_fragments VALUES(?,?,?)",
                       (row[0], source_url, json.dumps(fragments, ensure_ascii=False)))
            reviewed += 1
    if reviewed != 500:
        raise ValueError(f"Oczekiwano 500 kart z uzupełnieniami, otrzymano {reviewed}.")
    db.execute("""
        UPDATE projects SET title='Innowacyjna Biogazownia w Brodach – biometan z biogazu'
        WHERE source='NCBR' AND source_id=?
    """, (NCBR + "innowacyjna-biogazownia3",))
    live_count = add_live_reviews(db)
    db.execute("DROP TABLE project_words")
    build_lookup(db)
    print(f"Sprawdzono źródła dla {len(reviewed_cards) + live_count} kart. Poprawiono kategorię regułą tytułu dla {rule_count} kart.")


if __name__ == "__main__":
    with closing(sqlite3.connect(Path("sources/search.sqlite"))) as database, database:
        enrich(database)
