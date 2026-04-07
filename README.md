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

## Features

- **Element-Editor:** Erstellen und Bearbeiten von Salsa-Elementen mit technischer Validierung der Ein- und Ausgangszustände (Handhaltung, Position, Gewicht).
- **Figure-Builder:** Interaktives Zusammenstellen von Tanzfiguren aus vorhandenen Elementen mit Echtzeit-Validierung des Flows.
- **GitHub Integration (Auto-PR):** Neue Elemente und Figuren werden automatisch als Einzeldateien (`data/elements/` und `data/figures/`) als Pull Request in das Repository gesendet, um Datenverlust in ephemeren Umgebungen (wie Render) zu vermeiden.
- **Flow-Visualisierung:** Automatische Generierung von Mermaid.js-Diagrammen zur Visualisierung der Figurenabläufe.
- **Profil-Management:** Lokale Profile zur Verwaltung des eigenen Repertoires und personalisierte Lern-Empfehlungen.
- **Video-Integration:** Nahtlose Einbettung von YouTube-Videos für Elemente und Figuren.

## Lokale Ausführung

1. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
2. (Optional) GitHub-Integration konfigurieren:
   Erstelle eine `.env` Datei basierend auf `.env.example` und trage deinen `GITHUB_TOKEN` und `GITHUB_REPO` ein.
3. Anwendung starten:
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
- **Logik-Tests:** Kernlogik für Video-Integration, Editor-Funktionen und GitHub-Synchronisierung.
- **Speicher-Logik:** Verifizierung des neuen Einzeldatei-Speichersystems für Elemente und Figuren.

### Tests ausführen
Führe die Tests einfach mit folgendem Befehl aus:
```powershell
pytest -v
```
Der `PYTHONPATH` wird nun automatisch über die `pytest.ini` konfiguriert.

## Deployment
Die Anwendung läuft auf Render: [https://salsageek.onrender.com/](https://salsageek.onrender.com/)
Datenänderungen werden via Auto-PR permanent gesichert.