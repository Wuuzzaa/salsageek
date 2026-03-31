# SalsaGeek

## Architektur & Refactoring

SalsaGeek wurde im Hinblick auf Wartbarkeit und Erweiterbarkeit entwickelt. Vor dem Release im Master wurde ein umfassendes Refactoring durchgeführt:

- **Modulare Services:** Die Logik ist in spezialisierte Services unterteilt (`SalsaService`, `BuilderService`, `ElementEditorService`), die über `app.py` koordiniert werden.
- **Zustands-Validierung:** Das Kern-Datenmodell in `src/salsa_notation.py` validiert die physische Kompatibilität von Tanzelementen (Handhaltung, Position, Gewicht) über Mengen-Operationen.
- **Repertoire-Management:** Nutzer können über Profile ihren Fortschritt tracken und Empfehlungen für das nächste zu lernende Element erhalten.
- **Video-Integration:** YouTube-Videos können nahtlos in Elemente und Figuren eingebettet werden. Die Konvertierung erfolgt über einen zentralen Utility-Filter.
- **Frontend-Macros:** Wiederkehrende UI-Komponenten (z. B. Video-Galerien) sind in `templates/macros.html` als Jinja2-Makros gekapselt.

### Dokumentation
Alle Kern-Module verfügen über ausführliche Docstrings und Type Hints, um neuen Entwicklern den Einstieg zu erleichtern.

## Lokale Ausführung
```bash
python app.py
```
Öffne: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Automatisierte Tests
Die Anwendung verfügt über umfangreiche automatisierte Tests, die sowohl die technische Korrektheit der Tanz-Daten als auch die Erreichbarkeit der Webseiten sicherstellen.

### Was wird getestet?
- **Daten-Validierung:** Alle Elemente und Figuren in den YAML-Dateien werden auf technische Korrektheit geprüft (Handhaltung, Positionswechsel etc.).
- **Vollständige Seiten-Abdeckung:** Es wird für jedes Element und jede Figur automatisch geprüft, ob die Detailseite fehlerfrei lädt.
- **Visualisierungs-Check:** Die Flow-Visualisierung (Mermaid.js) wird für alle validen Figuren generiert und validiert.
- **Routenzugriff:** Alle Hauptseiten (Builder, Repertoire, etc.) werden auf Erreichbarkeit geprüft.
- **Logik-Tests:** Die Kernlogik für die Video-Integration (YouTube-Link-Konvertierung) und die Editor-Funktionen (Bearbeiten/Aktualisieren von Elementen) wird separat verifiziert.

### Tests ausführen
Um die Tests in der PowerShell zu starten, führe folgende Befehle aus:
```powershell
# PYTHONPATH setzen, damit die App gefunden wird
$env:PYTHONPATH = "."
pytest -v
```

## Deployment
Die Anwendung läuft auf Render: [https://salsageek.onrender.com/](https://salsageek.onrender.com/)