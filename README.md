<p align="center"><img src="web/market.svg" alt="Ikona straganu Ryneczku Innowacji" width="80"></p>

# Ryneczek Innowacji

**Wyszukiwarka polskich projektów dla szkół, uczelni, samorządów i innych instytucji.** Ryneczek zbiera rozproszone opisy projektów w jednym katalogu. Pomaga znaleźć rozwiązanie, sprawdzić, gdzie je testowano lub wdrożono, i porównać je z podobnymi projektami.

[**Otwórz Ryneczek Innowacji**](https://ryneczek-innowacji.onrender.com/) · [Przejdź do wyszukiwarki](https://ryneczek-innowacji.onrender.com/#discovery)

Projekt zespołu **Problem z głowy** przygotowany na HackNation 2026 w ramach wyzwania „Radar Innowacji” Podkarpackiego Centrum Innowacji. Zespół tworzą Maja Mastej, Bartłomiej Mastej i Wiktor Gogacz.

## Co można zrobić w Ryneczku

- **Wyszukać rozwiązanie po polsku.** Wpisz frazę lub wybierz filtry kategorii, technologii, miejsca zastosowania, TRL i etapu wdrożenia. Opcje w jednym filtrze działają jako alternatywy, a różne filtry można łączyć.
- **Sprawdzić podstawę wyniku.** Karta zawiera opis, link do źródła i dostępne informacje o testach, wdrażaniu lub zastosowaniu. Przycisk **Pokaż podobne** otwiera powiązane projekty.
- **Zgłosić własny projekt.** W instalacji z trwałym dyskiem formularz przyjmuje opis, link do materiałów i opcjonalne załączniki. Zgłoszenie trafia do zapisu poza katalogiem publicznym.

## Krótka demonstracja

| Wyszukaj | Co warto pokazać na karcie |
| --- | --- |
| **PETRA** | Analizator petrochemiczny. Moduł detekcyjny 1 GHz, seria pilotażowa i wdrożenie modułu do produkcji. |
| **BoltSense** | Śruby pomiarowe. Testy i skala użycia opisana przez NCBR oraz odsyłacz do oferty dystrybutora. |
| **biometan** | Innowacyjna Biogazownia w Brodach. Miejsce realizacji, instalacja demonstracyjna i źródła dotyczące uruchomienia produkcji. |

## Dane i wiarygodność

Katalog zawiera **46 661 rekordów** z ośmiu kolekcji źródłowych: Funduszy Europejskich, Interreg, NCBR, RAD-on, Bazy Innowacji Społecznych oraz trzech programów CORDIS. Rekord może opisywać projekt badawczy, prototyp, pilotaż lub działające rozwiązanie. Identyfikatory źródłowe pozwalają połączyć opisy z klasyfikacją i zachować odsyłacz do pierwotnego materiału.

- **Wdrożenie.** Filtr odróżnia wdrożenia udokumentowane w źródle od pilotaży, prac rozwojowych i potencjalnych zastosowań. Status dotyczy zakresu opisanego na karcie, np. modułu lub instalacji demonstracyjnej.
- **TRL.** Karty rozróżniają poziom deklarowany w źródle, szacunek z opisu i orientacyjny zakres przypisany według typu projektu. Zakres orientacyjny ma mniejszą pewność i nie potwierdza walidacji ani wdrożenia.
- **Podobieństwo i fragmenty.** Powiązania służą do dalszego porównania kart. Automatycznie wybrane fragmenty opisów mogą wymagać weryfikacji w materiale źródłowym.

## Jak działa wyszukiwanie

Frontend korzysta z **FastAPI** i katalogu **SQLite**. Najpierw stosowane są filtry, a indeks **FTS5** wybiera rekordy pasujące do wpisanych słów. Ranking bierze pod uwagę tytuł, opis i dostępne informacje o wdrożeniu. Publiczna wersja działa bez wywołań zewnętrznego modelu AI podczas wyszukiwania.

## Uruchomienie lokalne

W katalogu repozytorium uruchom:

```bash
docker build -t ryneczek-innowacji .
docker run --rm -p 8084:10000 ryneczek-innowacji
```

Otwórz [http://localhost:8084](http://localhost:8084). Obraz zawiera bazę katalogową i przygotowuje dane podczas budowania.

### Wdrożenie na Renderze

Utwórz usługę **Web Service** z repozytorium i wybierz środowisko **Docker**. Ustaw ścieżkę sprawdzania stanu na `/api/health`. Usługa nasłuchuje na porcie przekazanym w zmiennej `PORT`.

Aby włączyć **Dodaj projekt**, zamontuj trwały dysk, np. pod `/var/data`, i ustaw `RYNECZEK_SUBMISSIONS_DIR=/var/data`. Baza zgłoszeń i załączniki trafiają na dysk. Bez podłączonego dysku publiczna instalacja udostępnia katalog i wyszukiwarkę.

## Dalszy rozwój

Planujemy systematyczne aktualizacje danych, wyszukiwanie nowych realizacji w internecie i sprawdzanie dodatkowych źródeł o wdrożeniach. Kolejne kierunki to katalog potrzeb instytucji i analiza trendów dla twórców oraz inwestorów.
