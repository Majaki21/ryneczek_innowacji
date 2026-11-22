"""Project-by-project review of public sources, 22 November 2026."""

NCBR = "https://www.gov.pl/web/ncbr/"
REVIEWS = {
    "boltsense--nowatorskie-elementy-zlaczne-do-pomiaru-obciazen": (
        "yes", ("Elektronika i fotonika",),
        "BoltSense monitoruje naprężenia połączeń śrubowych, m.in. w młynach kulowych i turbinach wiatrowych. Projekt zintegrował łączność Bluetooth LE i LoRa z czujnikami oraz portalem pokazującym odczyty.",
        "Karta NCBR opisuje testy funkcjonalne oraz instalację ponad 4 tys. śrub przez Copper State Bolt & Nut Company. Dystrybutor pokazuje konfiguracje śrub pomiarowych i kompatybilne czytniki w ofercie.",
        (("NCBR – testy i skala zastosowania", NCBR+"boltsense--nowatorskie-elementy-zlaczne-do-pomiaru-obciazen"),
         ("Copper State – oferta BoltSense", "https://www.copperstate.com/boltsense-technology")),
    ),
    "comobility": (
        "potential", ("Zarządzanie miastem i infrastrukturą",),
        "Zespół badał, co wpływa na wybór sposobu dojazdu do szkoły. Połączył ankiety i dzienniczki podróży rodziców z warsztatami w szkołach, żeby zaprojektować interwencje dotyczące mobilności.",
        "Raport z 2022 r. dokumentuje pierwszą rundę badań w trzech warszawskich szkołach. Dane miały zasilić model ruchu i projektowanie działań wokół szkół.",
        (("NCBR – metoda i zespół projektu", NCBR+"comobility"),
         ("CoMobility – raport z badań szkolnych", "https://comobility.edu.pl/publications/podsumowanie-i-rundy-badan-ankietowych-w-szkolach-podstawowych/")),
    ),
    "demonstracja-autorskiej-technologii-wytwarzania-komponentow-i-elementow-kompozytowych-asset": (
        "yes", ("Materiały i technologie produkcji",),
        "A.S.SET wykorzystuje jednoskładnikową żywicę epoksydową i rozwiniętą linię demonstracyjną do produkcji prepregów, czyli półproduktów do wytwarzania kompozytów. Projekt objął też materiały uniepalnione do transportu.",
        "NCBR dokumentuje wdrożenie uniepalnionego NEMpreg w kolejnictwie i zastosowanie kompozytów przekładkowych w platformach autobusowych. Producent publikuje parametry i zastosowania rodziny NEMpreg.",
        (("NCBR – demonstrator i zastosowania transportowe", NCBR+"demonstracja-autorskiej-technologii-wytwarzania-komponentow-i-elementow-kompozytowych-asset"),
         ("New Era Materials – rodzina materiałów NEMpreg", "https://neweramaterials.com/pl/product/nempreg-2/")),
    ),
    "innowacyjna-biogazownia3": (
        "in_progress", ("Energetyka",),
        "Instalacja w Brodach oczyszcza biogaz do biometanu. Projekt obejmuje również wykorzystanie pofermentu jako surowca do produkcji nawozów.",
        "NCBR opisuje uruchomienie produkcji biometanu w obiekcie demonstracyjnym. Kujawsko-Pomorski Ośrodek Doradztwa Rolniczego wskazuje instalację na terenie gospodarstwa doświadczalnego Uniwersytetu Przyrodniczego w Poznaniu.",
        (("NCBR – uruchomienie produkcji biometanu", NCBR+"innowacyjna-biogazownia-rusza-z-produkcja-biometanu"),
         ("KPODR – opis instalacji w Brodach", "https://www.kpodr.pl/racjonalne-wykorzystanie-odnawialnych-zrodel-energii/")),
    ),
    "inteligentne-sieci-elektroenergetyczne-na-obszarach-wiejskich--rigrid": (
        "yes", ("Energetyka",),
        "W ramach RIGRID opracowano narzędzie do nadzoru nad rozproszonymi instalacjami energetycznymi. Oferta Electrum opisuje monitoring urządzeń takich jak falowniki, liczniki i czujniki nasłonecznienia we wspólnym systemie.",
        "NCBR dokumentuje komercjalizację oprogramowania przez Electrum w modelu SaaS. Według relacji wykonawcy w ciągu 24 miesięcy objęło ono instalacje OZE o łącznej mocy ponad 1 GW.",
        (("NCBR – komercjalizacja i skala wykorzystania", NCBR+"inteligentne-sieci-elektroenergetyczne-na-obszarach-wiejskich--rigrid"),
         ("Electrum – opis platformy EMACS", "https://electrum.pl/emacs")),
    ),
    "inteligentny-system-do-budowy-i-utrzymywania-relacji-z-klientami--dmsales": (
        "yes", ("Informatyka i telekomunikacja",),
        "DMSales to oferowana przez DBMS platforma wspierająca wyszukiwanie i segmentację odbiorców biznesowych oraz obsługę kampanii. Zadanie B+R dotyczyło rozwinięcia istniejącej platformy.",
        "Wykonawca opisuje powiązanie produktu z projektem finansowanym przez NCBR. Regulamin działającej usługi potwierdza zakres funkcji oddanych użytkownikom platformy.",
        (("DBMS – zakres projektu B+R", "https://dbms.com.pl/platforma-dmsales/"),
         ("DMSales – funkcje działającej usługi", "https://dmsales.com/regulamin/")),
    ),
    "jednolity-system-antyplagiatowy": (
        "yes", ("Informatyka i telekomunikacja",),
        "JSA analizuje teksty prac dyplomowych i przygotowuje raport podobieństwa dla promotora. Porównuje tekst m.in. z repozytorium prac dyplomowych, bazą postępowań awansowych oraz treściami dostępnymi w internecie.",
        "OPI utrzymuje wersję produkcyjną systemu. Według centrum pomocy JSA działa w polskim szkolnictwie wyższym od 2019 r. i skorzystało z niego ponad 350 jednostek.",
        (("OPI – źródła porównania i zastosowanie na uczelniach", "https://jsa-cp.opi.org.pl/o-jsa/"),
         ("OPI – dokumentacja wersji produkcyjnej", "https://jsa-cp.opi.org.pl/baza-wiedzy-skroty/jsa/")),
    ),
    "noctiluca": (
        "in_progress", ("Technologie chemiczne", "Elektronika i fotonika"),
        "Noctiluca rozwija organiczne emitery światła do wyświetlaczy OLED. Projekt obejmuje materiały do konwencjonalnych ekranów oraz do formulacji tuszy wykorzystywanych w druku OLED.",
        "Karta NCBR opisuje testowanie emiterów przez LG Display i ocenę materiałów do tuszy przez Juhua. Status dotyczy testów u partnerów wskazanych w źródle.",
        (("NCBR – materiały i testy u partnerów", NCBR+"noctiluca"),
         ("Noctiluca – prezentacja o rozwoju i komercjalizacji", "https://noctiluca.eu/wp-content/uploads/2025/06/NCL_prezentacja-WZA_VI-2025_2025.06.24_sent.pdf")),
    ),
    "integrowane-nawadnianie": (
        "potential", ("Rolnictwo i żywność",),
        "Instytut Ogrodnictwa w Skierniewicach zbudował prototyp sterownika nawadniania szkółek roślin ozdobnych. Model wylicza godzinowe potrzeby wodne, wykorzystując m.in. dane ze stacji meteorologicznej i czujników parametrów podłoża.",
        "Źródło dokumentuje stanowisko z lizymetrami oraz pomiar temperatury, wilgotności i zasolenia. Potencjalni odbiorcy to szkółki roślin ozdobnych i gospodarstwa prowadzące uprawy pod osłonami.",
        (("NCBR – prototyp i stanowisko badawcze", NCBR+"integrowane-nawadnianie"),),
    ),
    "inteligentna-dokladna-tokarka-do-regeneracji-zestawow-kolowych-pojazdow-szynowych": (
        "in_progress", ("Kolejnictwo i transport", "Materiały i technologie produkcji"),
        "Tokarka KOLTECH wykorzystuje pomiary temperatury konstrukcji i sił skrawania. Układ sterowania na tej podstawie koryguje ścieżkę narzędzia podczas regeneracji zestawu kołowego.",
        "NCBR opisuje zrealizowanie samokompensacji w tokarce produkcyjnej. KOLTECH pokazuje ofertę tokarek kołowych. Etap karty dotyczy wykonania funkcji w maszynie.",
        (("NCBR – opracowane funkcje i realizacja w tokarce", NCBR+"inteligentna-dokladna-tokarka-do-regeneracji-zestawow-kolowych-pojazdow-szynowych"),
         ("KOLTECH – katalog maszyn", "https://koltech.com.pl/produkty/maszyny")),
    ),
    "innowacyjny-kompleksowy-system-zbiorki-i-recyklingu-odpadow": (
        "yes", ("Woda, odpady i środowisko",),
        "System łączy recyklomaty z aplikacją ECOWallet. Użytkownik oddaje opakowanie, a aplikacja przypisuje punkty, które można wymieniać na nagrody lub zniżki.",
        "Starostwo Powiatowe w Bochni potwierdza uruchomienie recyklomatu w ramach projektu NCBR prowadzonego przez EcoTech System. To konkretne miejsce zastosowania rozwiązania.",
        (("NCBR – działanie systemu i aplikacji", NCBR+"innowacyjny-kompleksowy-system-zbiorki-i-recyklingu-odpadow"),
         ("Powiat Bocheński – działający recyklomat", "https://www.powiatbochenski.pl/aktualnosci/recyklomat-juz-dziala.html")),
    ),
}
DOMAINS = {"comobility": "Administracja publiczna"}
TRL = {
    "boltsense--nowatorskie-elementy-zlaczne-do-pomiaru-obciazen": (8,9),
    "demonstracja-autorskiej-technologii-wytwarzania-komponentow-i-elementow-kompozytowych-asset": (8,9),
    "innowacyjna-biogazownia3": (6,8),
    "inteligentne-sieci-elektroenergetyczne-na-obszarach-wiejskich--rigrid": (8,9),
    "inteligentny-system-do-budowy-i-utrzymywania-relacji-z-klientami--dmsales": (8,9),
    "jednolity-system-antyplagiatowy": (9,9),
    "noctiluca": (4,6),
    "integrowane-nawadnianie": (4,6),
    "inteligentna-dokladna-tokarka-do-regeneracji-zestawow-kolowych-pojazdow-szynowych": (6,8),
    "innowacyjny-kompleksowy-system-zbiorki-i-recyklingu-odpadow": (7,9),
}
