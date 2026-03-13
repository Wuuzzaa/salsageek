# SalsaGeek

**SalsaGeek** ist eine kleine Python-Web-App zur strukturierten Lernhilfe für **Salsa LA Style On1** aus Sicht des **Leaders**.

Die Anwendung hilft dabei,

- bekannte Basiselemente und Figuren zu erfassen,
- aus einem persönlichen Repertoire ableitbare Figuren anzuzeigen,
- sinnvolle nächste Lernelemente zu empfehlen,
- und eigene Figuren-Sequenzen auf technische Kompatibilität zu prüfen.

Die Domäne wird nicht frei im Code „erfunden“, sondern durch **strukturierte YAML-Daten** beschrieben.  
Dadurch ist das Projekt inhaltlich erweiterbar, ohne dass für jede neue Figur oder jedes neue Element Programmcode geändert werden muss.

---

## Projektziel

Das Projekt soll eine **leicht erweiterbare Lern- und Analyse-App für Salsa-Figuren** sein.

### Kurz gesagt

Ein Nutzer markiert, welche Tanz-Elemente er bereits beherrscht.  
Die Anwendung kann daraus ableiten:

1. **Welche Figuren bereits tanzbar sind**
2. **Welche Elemente als Nächstes am meisten bringen**
3. **Ob eine eigene Sequenz technisch zusammenpasst**

### Langfristige Richtung

SalsaGeek soll sich von einer einfachen persönlichen Lernhilfe zu einem **fachlich sauberen, datengetriebenen Salsa-Wissens- und Trainingssystem** entwickeln.

Mögliche Ausbauziele:

- bessere Visualisierung von Zustandsübergängen
- detailliertere Element- und Figurenansichten
- mehrere Profile / Nutzer
- Fortschrittsverfolgung
- didaktische Lernpfade
- Trainingsmodus
- mobile Nutzung

---

## Aktueller Stand

Die Anwendung ist aktuell als **Flask-Web-App** umgesetzt.

### Bereits vorhanden

- **Flask-basierte Web-Oberfläche**
- **Bootstrap 5** für schnelles, sauberes UI
- Laden der Domänendaten aus YAML
- Laden und Speichern eines persönlichen Profils in `profil.yaml`
- Anzeige ausführbarer Figuren
- Anzeige von Lernempfehlungen
- Figuren-Baukasten zur Sequenzprüfung
- Validierung von Figuren beim Laden

### Umstellung gegenüber dem früheren Stand

Das Projekt war ursprünglich als **Konsolenanwendung** konzipiert.  
Die UI wurde auf eine **einfache Web-App** umgestellt, die weiterhin vollständig in Python läuft.

Die Umstellung war sinnvoll, weil:

- Auswahl und Pflege des Repertoires im Browser deutlich angenehmer sind
- Ergebnisse strukturierter dargestellt werden können
- die App leichter nutzbar und erweiterbar wird
- die bestehende Kernlogik weitgehend unverändert weiterverwendet werden kann

Die Fachlogik liegt weiterhin getrennt von der Darstellungsschicht, was für Wartbarkeit und Ausbau sehr hilfreich ist.

---

## Kernidee des Datenmodells

Das Projekt modelliert Salsa nicht nur über Namen von Figuren, sondern über **Elemente mit Zuständen**.

Ein Element beschreibt unter anderem:

- Name und ID
- Beschreibung
- Anzahl Counts
- Schwierigkeit / Level
- Tags
- **Vorbedingung (`pre`)**
- **Nachbedingung (`post`)**
- optionale Leader-Aktionen
- optionale Führungssignale
- optionale Hinweise

### Warum das wichtig ist

Figuren werden als **Sequenzen von Elementen** definiert.  
Eine Sequenz ist nur gültig, wenn der Endzustand eines Elements mit dem Anfangszustand des nächsten Elements kompatibel ist.

Dadurch wird aus einer bloßen Liste von Begriffen ein kleines **regelbasiertes Bewegungsmodell**.

---

## Fachliche Konzepte

### Element
Ein einzelner technischer Baustein, zum Beispiel:

- Basic Step
- Cross Body Lead
- Turn
- Transition
- Hammerlock Entry
- Copa Exit

### Figure
Eine benannte Folge mehrerer Elemente.

### SalsaState
Ein Übergabezustand zwischen zwei Elementen.  
Er beschreibt, in welcher Konstellation sich Leader und Follower befinden.

Aktuell modellierte Zustandsbereiche sind unter anderem:

- Handverbindung
- Position
- Slot
- Gewichtsverteilung des Leaders

### Profil
Ein persönlicher Wissensstand: Welche Elemente sind bereits bekannt?

---

## Was die App aktuell kann

## 1. Startseite

Die Startseite zeigt eine kompakte Übersicht:

- Anzahl geladener Elemente
- Anzahl geladener Figuren
- Anzahl bekannter Elemente im Profil
- aktuelles Level
- Anzahl ausführbarer Figuren
- Anzahl ungültiger Figuren

Zusätzlich ist sie Einstiegspunkt für die wichtigsten Bereiche.

---

## 2. Repertoire bearbeiten

Auf der Repertoire-Seite kann der Nutzer angeben, welche Elemente bereits beherrscht werden.

### Aktuelles Verhalten

- Elemente werden nach Level gruppiert dargestellt
- bekannte Elemente können per Checkbox markiert werden
- das Ergebnis wird in `profil.yaml` gespeichert
- beim Laden werden veraltete oder unbekannte IDs automatisch bereinigt

### Ziel dieses Bereichs

Das Repertoire ist die zentrale Eingabe der App.  
Fast alle anderen Funktionen bauen darauf auf.

---

## 3. Figuren anzeigen

Die Figuren-Seite zeigt alle Figuren, die mit dem aktuellen Repertoire ausführbar sind.

### Grundlage

Eine Figur ist ausführbar, wenn alle in ihrer Sequenz enthaltenen Elemente im Profil vorhanden sind.

Zusätzlich werden beim Laden nur gültige Figuren berücksichtigt, sofern sie technisch korrekt validiert wurden.

### Anzeige aktuell

- Name
- Beschreibung
- Level
- Sequenz in lesbarer Form
- Count-Anzahl
- Tags
- optionale Notizen

---

## 4. Lernempfehlungen

Die Empfehlungslogik schlägt Elemente vor, die den größten Nutzen für den nächsten Lernschritt haben.

### Aktuelle Heuristik

Ein Element ist umso interessanter, wenn es:

- neue Figuren direkt freischaltet
- Figuren in Reichweite bringt, denen danach nur noch ein Element fehlt

Die Berechnung nutzt den aktuellen Profilstand plus eine hypothetische Erweiterung um genau ein weiteres Element.

### Ziel

Nicht einfach „irgendwas als Nächstes lernen“, sondern sinnvoll priorisieren.

---

## 5. Figuren-Baukasten

Der Baukasten erlaubt die manuelle Eingabe einer Sequenz aus Element-IDs.

Beispiel:
text basic_open, cbl, follower_right_turn

ie App prüft dann:

- ob alle IDs existieren
- ob jedes Element auf das vorherige folgen darf
- wie viele Counts die Sequenz insgesamt hat
- welcher Start- und Endzustand entsteht

### Nutzen

Der Baukasten ist aktuell das direkteste Werkzeug, um die eigentliche Fachlogik sichtbar zu machen.

Er ist damit nicht nur eine Nutzerfunktion, sondern auch ein gutes Diagnose- und Testwerkzeug.

---

## Projektstruktur

text salsageek/ ├─ app.py ├─ profil.yaml ├─ data/ │ ├─ elements.yaml │ └─ figures.yaml ├─ src/ │ └─ salsa_notation.py ├─ templates/ │ ├─ base.html │ ├─ index.html │ ├─ repertoire.html │ ├─ figuren.html │ ├─ empfehlungen.html │ └─ builder.html └─ static/ └─ css/ └─ app.css

---

## Rolle der einzelnen Dateien

### `app.py`
Web-Einstiegspunkt der Anwendung.

Verantwortlich für:

- Flask-Routen
- Laden und Speichern des Profils
- Aufbereitung der Daten für Templates
- Verbindung zwischen Fachlogik und UI

### `src/salsa_notation.py`
Kernlogik und Domänenmodell.

Verantwortlich für:

- Datenklassen
- Laden der YAML-Daten
- Zustandsprüfung
- Figurenvalidierung
- Ermittlung ausführbarer Figuren
- Empfehlungslogik

### `data/elements.yaml`
Definition aller bekannten Elemente.

### `data/figures.yaml`
Definition benannter Figuren als Sequenzen von Element-IDs.

### `profil.yaml`
Einfaches Persistenzformat für das aktuelle Nutzerprofil.

### `templates/`
HTML-Templates der Web-Oberfläche.

### `static/css/app.css`
Zusätzliche Gestaltung über Bootstrap hinaus.

---

## Architekturüberblick

Die Anwendung ist aktuell grob in drei Schichten aufgeteilt:

### 1. Daten
YAML-Dateien beschreiben Elemente und Figuren.

### 2. Fachlogik
Python-Code in `src/salsa_notation.py` interpretiert diese Daten und wendet Regeln an.

### 3. Präsentation
Flask + Jinja-Templates + Bootstrap stellen die Ergebnisse im Browser dar.

### Positiv an dieser Struktur

- gut verständlich
- schnell erweiterbar
- geringe Einstiegshürde
- Fachlogik ist nicht mit HTML vermischt
- UI kann weiterentwickelt werden, ohne das Modell neu zu denken

---

## Installation

Voraussetzungen:

- Python 3.12
- bestehendes `virtualenv`
- installierte Pakete:
  - `flask`
  - `pyyaml`

---

## Anwendung starten
bash python app.py

Danach im Browser öffnen:
text [http://127.0.0.1:5000](http://127.0.0.1:5000)

---
---

## Bedienung

## Repertoire pflegen

1. Seite **Repertoire** öffnen
2. bekannte Elemente markieren
3. speichern

## Figuren ansehen

1. Seite **Figuren** öffnen
2. ausführbare Figuren prüfen

## Empfehlungen ansehen

1. Seite **Empfehlungen** öffnen
2. nächste sinnvolle Elemente prüfen

## Eigene Sequenz testen

1. Seite **Baukasten** öffnen
2. IDs kommasepariert eingeben
3. Ergebnis prüfen

---

## Beispiel für den Workflow

1. Profil ist leer
2. Nutzer markiert erste Grundelemente
3. App zeigt erste tanzbare Figuren
4. Empfehlungen schlagen den nächsten sinnvollen Baustein vor
5. Nutzer testet im Baukasten eigene Sequenzen
6. YAML-Daten werden schrittweise erweitert
7. Das System wächst inhaltlich mit dem Fachmodell

---

## Stärken des aktuellen Projekts

### 1. Datengetriebener Ansatz
Das ist der wichtigste Pluspunkt.

Neue Inhalte werden überwiegend in YAML beschrieben, nicht im Python-Code hart verdrahtet.

### 2. Fachlogik ist schon sinnvoll abstrahiert
Das Projekt denkt in Zuständen und Kompatibilität, nicht nur in Listen und Schlagwörtern.

### 3. Gute Basis für Erweiterung
Die Web-App ist einfach, aber nicht wegwerfbar.  
Sie ist eine gute Zwischenstufe zwischen Prototyp und echter Anwendung.

### 4. Verständlicher Scope
Das Projekt versucht aktuell nicht, alles zu lösen.  
Das ist gut. Es konzentriert sich auf ein klar umrissenes Modell.

---

## Grenzen des aktuellen Stands

So nützlich der jetzige Stand ist: Es gibt noch einige bewusste Vereinfachungen.

### 1. Nur ein lokales Profil
Aktuell gibt es nur `profil.yaml` als Einzelprofil.

### 2. Keine Datenbank
Für den aktuellen Scope okay, aber nicht skalierbar für mehrere Nutzer oder Historie.

### 3. Empfehlungen noch heuristisch
Die Empfehlungslogik ist sinnvoll, aber noch relativ einfach.

### 4. Wenig Detailansichten
Elemente und Figuren werden kompakt angezeigt, aber noch nicht tief explorierbar.

### 5. Keine Bearbeitung der Domänendaten über die UI
Elemente und Figuren werden nur aus YAML geladen, nicht im Browser gepflegt.

### 6. Keine Tests
Die Domänenlogik eignet sich sehr gut für automatisierte Tests, diese sollten ergänzt werden.

---

## Sinnvolle nächste Änderungen

Die folgenden Änderungen halte ich für besonders sinnvoll.

## Priorität A – direkt lohnend

### 1. `requirements.txt` ergänzen
Aktuell sollten die relevanten Laufzeitabhängigkeiten explizit dokumentiert werden.

Empfohlen:
text Flask PyYAML

Optional mit festen Versionen.

### 2. Flash-Messages statt Query-Parameter
Das Speichern im Repertoire wird aktuell über einen URL-Parameter signalisiert.  
Besser wäre die Standard-Flask-Lösung mit `flash()`.

### 3. Aktive Navigation hervorheben
Die Navbar sollte visuell zeigen, auf welcher Seite man sich befindet.

### 4. Such- und Filterfunktion im Repertoire
Bei wachsender Elementzahl wird die Checkbox-Seite schnell lang.  
Suche nach Name, ID, Tag und optional Level wäre sehr hilfreich.

### 5. Detailansichten für Elemente und Figuren
Sinnvoll wären Seiten wie:

- `/element/<id>`
- `/figur/<id>`

Dort könnten vollständige Zustände, Signale, Aktionen und Notizen angezeigt werden.

---

## Priorität B – fachlich sehr wertvoll

### 6. Tests für die Kernlogik
Besonders geeignet für Tests sind:

- Laden von Elementen
- Auflösen von `same`
- Zustandskompatibilität
- Validierung von Figuren
- Empfehlungslogik
- Baukasten-Prüfungen

Ein kleines Testpaket würde die Weiterentwicklung deutlich sicherer machen.

### 7. Bessere Fehlerdarstellung für ungültige Figuren
Ungültige Figuren werden bereits erkannt.  
Das sollte stärker sichtbar und verständlich aufbereitet werden, eventuell mit eigener Diagnoseseite.

### 8. Detailliertere Empfehlungslogik
Langfristig könnten Empfehlungen zusätzlich berücksichtigen:

- Anzahl neu erreichbarer Übergänge
- didaktische Progression
- persönliche Lernpfade
- Seltenheit / Schwierigkeit / Stilfamilien
- Wiederverwendbarkeit eines Elements in vielen Figuren

### 9. Domänenmodell weiter präzisieren
Mögliche fachliche Erweiterungen:

- klarere Modellierung der Timing-Phasen
- stärkere Trennung zwischen Griffzustand und Körperposition
- explizitere Übergangsregeln
- Varianten / Aliase / Familien von Elementen

---

## Priorität C – Produktreife und Komfort

### 10. Mehrere Profile oder Nutzer
Statt einer einzelnen `profil.yaml` wären mittelfristig sinnvoll:

- mehrere lokale Profile
- oder SQLite-basierte Nutzerprofile

### 11. Historie / Fortschritt
Nützlich wären:

- wann ein Element gelernt wurde
- Fortschrittsstatistik
- zuletzt freigeschaltete Figuren
- Lernverlauf pro Woche

### 12. Editierbare Inhalte im Admin-Bereich
Langfristig könnten Elemente und Figuren auch über eine geschützte UI bearbeitet werden.  
Für den aktuellen Stand ist YAML aber noch die richtige Wahl.

### 13. Export / Import
Sinnvoll wären Exportmöglichkeiten für Profile oder Trainingsstände.

---

## Empfohlene technische Richtung

Die aktuelle Architektur ist für den jetzigen Scope passend.  
Ich würde sie **nicht** vorschnell komplizierter machen.

### Was ich aktuell beibehalten würde

- Flask
- Jinja-Templates
- Bootstrap
- YAML als inhaltliche Datenquelle
- `profil.yaml` als einfache lokale Speicherung

### Was ich als Nächstes ergänzen würde

1. Tests
2. Detailseiten
3. Suche/Filter
4. `requirements.txt`
5. kleinere UX-Verbesserungen

### Was ich noch nicht sofort einführen würde

- große Datenbankarchitektur
- Frontend-Framework
- REST-API-first-Ansatz
- Benutzerverwaltung
- komplexes Rollenmodell

Das Projekt ist aktuell stark genug, um nützlich zu sein, aber noch klein genug, um einfach zu bleiben.  
Diese Balance ist wertvoll.

---

## Für Menschen: Worum es in diesem Projekt wirklich geht

SalsaGeek ist kein beliebiger Figurenkatalog.  
Der interessante Kern ist:

> Tanzwissen wird als kombinierbare, prüfbare Struktur modelliert.

Das Projekt versucht also, Tanz nicht nur zu beschreiben, sondern in kleinen Teilen logisch zusammensetzbar zu machen.

Genau darin steckt der eigentliche Charme des Projekts.

---

## Für KI-Assistenten: Projektverständnis in Kurzform

### Projektart
Kleine datengetriebene Flask-Web-App in Python.

### Domäne
Salsa LA Style On1, Leader-Perspektive.

### Hauptobjekte
- `Element`
- `Figure`
- `SalsaState`

### Datenquellen
- `data/elements.yaml`
- `data/figures.yaml`
- `profil.yaml`

### Hauptzweck
Aus einem bekannten Repertoire ableiten:

- ausführbare Figuren
- sinnvolle nächste Elemente
- technische Gültigkeit eigener Sequenzen

### Wichtige technische Eigenschaft
Die Fachlogik lebt vor allem in `src/salsa_notation.py`;  
`app.py` ist primär Web- und Orchestrierungsschicht.

### Entwicklungsrichtung
Mehr Analyse, bessere Exploration, didaktisch stärkere Empfehlungen, bessere UI, aber weiterhin einfache Python-basierte Architektur.

---

## Nicht-Ziele im aktuellen Stand

Aktuell ist das Projekt **nicht**:

- eine vollwertige Tanzschul-Plattform
- ein Social- oder Community-System
- ein Video-Trainingsportal
- ein komplexes Multi-User-SaaS
- ein pixelperfektes Designprodukt

Und das ist völlig in Ordnung.

---

## Fazit

SalsaGeek ist aktuell eine **kleine, klare, fachlich interessante Web-App** mit einer guten Grundlage:

- datengetrieben
- domänenorientiert
- in Python einfach erweiterbar
- für Lernlogik gut geeignet

Der wichtigste nächste Schritt ist aus meiner Sicht nicht „mehr Technik“, sondern **mehr Struktur und mehr Explizitheit**:

- Tests
- Detailansichten
- bessere Exploration
- nachvollziehbare Empfehlungen
- sauber dokumentierte Abhängigkeiten

Wenn diese Punkte ergänzt werden, kann aus dem aktuellen Projekt sehr gut ein robustes, charmantes Spezialwerkzeug für Salsa-Lernlogik werden.