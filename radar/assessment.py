def criterion(label, evidence, reason, missing):
    evidence = evidence.strip()
    return {
        "label": label,
        "result": "Udokumentowane" if evidence else "Brak danych",
        "reason": reason if evidence else missing,
        "evidence": evidence or "brak danych",
    }


def assessment(item, links):
    confirmed = any(link["role"] == "wdrażający" and link["confirmed"] for link in links)
    criteria = [
        criterion("Udokumentowana potrzeba", item["problem_evidence"],
                  "Zapisano podstawę rozpoznania problemu.",
                  "Dodaj obserwację lub pomiar pokazujący, kogo i jak często dotyczy problem."),
        criterion("Dowody działania", item["evidence"],
                  "Karta zawiera fragment materiału opisującego działanie. Zobacz status źródła.",
                  "Brakuje obserwacji lub pomiarów działania rozwiązania."),
        criterion("Warunki wdrożenia w innej instytucji", item["conditions"],
                  "Karta wskazuje warunki, które kolejna instytucja musi sprawdzić.",
                  "Ustal wymagane zasoby, osobę odpowiedzialną i warunki pilotażu."),
    ]
    if item["source"] and not item["demo"] and item["evidence"].strip():
        criteria[1]["result"] = "Materiał do weryfikacji"
        criteria[1]["reason"] = "Import zachował fragment źródła do oceny przez recenzenta."
    tags = {tag.casefold() for tag in item["tags"]}
    step = "Ustal problem z odbiorcami i zaplanuj walidację."
    recipient = "Właściciel zgłoszenia i zainteresowani użytkownicy"
    metric = ""
    if item["stage"] == "pomysł" and "szkolnictwo" in tags:
        step = "Uzgodnij miernik, zmierz stan wyjściowy i przeprowadź pilotaż w dwóch klasach."
        recipient = "Dyrekcja szkoły i nauczyciele obu klas"
        metric = (
            "Porównaj liczbę minut potrzebnych na rozpoczęcie pracy przed pilotażem i w jego trakcie."
            if "organizacj" in f"{item['title']} {item['summary']}".casefold()
            else "Porównaj wartość wskaźnika uzgodnionego z nauczycielami przed pilotażem i w jego trakcie."
        )
    elif item["stage"] == "wdrożenie" and item["evidence"].strip() and item["conditions"].strip():
        step = "Sprawdź warunki transferu i uzgodnij zakres pilotażu."
        recipient = item["recipient"] or "Instytucja o podobnej potrzebie"
        metric = item["metric"]
    elif item["stage"] != "pomysł":
        step = "Uzupełnij dowody działania i warunki kolejnego wdrożenia."
    return {
        "źródło": "jest" if item["source"] else "brak publicznego źródła",
        "wdrożenie": "potwierdzone przez instytucję" if confirmed else "brak potwierdzenia",
        "następny krok": step,
        "criteria": criteria,
        "recipient": recipient,
        "metric": metric,
    }
