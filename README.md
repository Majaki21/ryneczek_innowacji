# Ryneczek Innowacji – publiczne demo

Opublikuj zawartość tego folderu w prywatnym repozytorium GitHub. Na Render
utwórz Web Service połączony z repozytorium, wybierz Docker i ustaw ścieżkę
sprawdzania stanu na `/api/health`. Publiczny adres HTTPS pojawi się po wdrożeniu.

Katalog działa publicznie. Aby włączyć formularz, w Render podłącz Persistent
Disk do usługi i ustaw `RYNECZEK_SUBMISSIONS_DIR` na jego ścieżkę montowania,
np. `/var/data`. Formularz zapisuje zgłoszenia i załączniki na dysku usługi,
a zgłoszenia nie są publikowane w katalogu. Panel demonstracyjny pozostaje
niedostępny z internetu. Po wdrożeniu przetestuj zapis przykładowego zgłoszenia.

Wartość „TRL 1–9 · brak danych do zawężenia” oznacza pełną skalę bez oceny
dojrzałości. Takie karty nadal odpowiadają filtrowi „Brak danych”.
