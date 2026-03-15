# Source-Code Dokumentation (MVC + Services)

Diese Dokumentation beschreibt die Struktur des Projekts und erklärt, welche Datei welche Aufgabe hat und welche Methoden in welchem Ablauf aufgerufen werden. Ziel ist eine klare Trennung zwischen Benutzeroberfläche (Views), Ablaufsteuerung (Controller), Maschinenlogik (Services) und Datenhaltung (Models/SQLite).

## Architektur-Idee

Das Projekt besteht aus zwei „Welten“, die bewusst getrennt sind:

- **Maschinenwelt**: alles, was echte Hardware bewegt oder Statusbits ausliest (Homing, Fahren, Pumpen, busy/idle).
- **Datenwelt**: alles, was Stammdaten in SQLite pflegt (Zutaten, Cocktails, Pumpen-Konfiguration, Rezepte).

Die **Views** sind nur die Oberfläche. Sie machen ausschließlich Ein-/Ausgabe (`input`, `print`) und rufen Controller-Methoden auf.  
Die **Controller** bündeln Anwendungsfälle (Use-Cases).  
Die **Services** kapseln Ablauf- und Hardware-Logik (busy-warten, I2C-Kommandos).  
Die **Models** kapseln SQLite-Zugriffe (CRUD).

Merksatz:

- View fragt den Benutzer und zeigt Ergebnisse an  
- Controller koordiniert einen Use-Case  
- Service führt Ablauf-/Hardware-Schritte sicher aus  
- Model liest/schreibt Datenbank

---

## Projektstruktur

- `View/`
  - `console_view.py`
  - `cocktail_view.py`
  - `calibration_view.py`
  - `admin_view.py`
- `Controller/`
  - `mix_controller.py`
  - `pump_controller.py`
  - `admin_controller.py`
- `Services/`
  - `mix_engine.py`
  - `pump_calibration_service.py`
  - `status_monitor.py`
  - `status_service.py`
- `Model/`
  - `mix_model.py`
  - `pump_model.py`
  - `ingredient_model.py`
  - `cocktail_model.py`
- `Hardware/`
  - `i2C_logic.py`
- `main.py`

---

## Views (Benutzeroberfläche)

### `View/console_view.py`
**Aufgabe:** Hauptmenü („Router“) und Weiterleitung in Unterviews.  
**Outcome:** Startet die passenden Untermenüs und zeigt Live-Status.

**Ruft auf:**
- `CocktailView.run_mix_flow()` (Cocktail mischen)
- `CalibrationView.run()` (Kalibrierung)
- `AdminView.run()` (Admin)
- `MixController.get_status()` (Live-Status)

---

### `View/cocktail_view.py`
**Aufgabe:** Cocktail-Auswahl und Mix starten (z.B. über Cocktail-ID).  
**Outcome:** Ein Mixvorgang wird ausgelöst und das Rezept wird ausgegeben.

**Ruft auf:**
- `MixController.mix_cocktail(cocktail_id)`

---

### `View/calibration_view.py`
**Aufgabe:** Kalibrierungs-Menü. Hardware-nahes Setup (Pumpe laufen lassen, Flow-Rate speichern, Position setzen, Schlitten bewegen).  
**Outcome:** Parameter wie `flow_rate_ml_s` und `position_steps` werden getestet und gespeichert.

**Ruft auf:**
- `PumpController.list_pumps()`
- `PumpController.ensure_homed()`
- `PumpController.move_to_position(steps)`
- `PumpController.run_pump_for_calibration(pump_number, seconds)`
- `PumpController.save_flow_rate_from_measurement(pump_number, measured_ml, seconds)`
- `PumpController.set_position_steps(pump_number, steps)`

---

### `View/admin_view.py`
**Aufgabe:** Stammdaten-Verwaltung (Zutaten, Cocktails, Pumpen-Datensätze, später Rezepte).  
**Outcome:** Datensätze werden in SQLite angelegt/gelöscht/aktualisiert.

**Ruft auf:**
- `AdminController.list_ingredients() / add_ingredient() / delete_ingredient()`
- `AdminController.list_cocktails() / add_cocktail() / delete_cocktail()`
- `AdminController.add_pump() / delete_pump()`
- Optional für Pumpen-Zuordnung:
  - `PumpController.assign_ingredient(pump_number, ingredient_id)`  
  (oder alternativ als reine DB-Operation im `AdminController`)

---

## Controller (Use-Cases / Ablaufsteuerung)

### `Controller/mix_controller.py`
**Aufgabe:** Use-Case „Cocktail mischen“.  
**Outcome:** Liest Rezeptdaten aus der DB, startet den Maschinenablauf und liefert das Rezept zurück.

**Greift zu auf:**
- `Model/mix_model.py` (Rezeptdaten)
- `Services/mix_engine.py` (Hardware-Ablauf)

**Typischer Ablauf:**
1. `MixController.mix_cocktail(cocktail_id)`
2. `MixModel.get_full_mix_data(cocktail_id)` liefert Zutaten + Pumpendaten (sortiert)
3. `MixEngine.mix_cocktail(mix_data)` führt Homing/Move/Pump sequenziell aus
4. Ergebnis (Rezeptdaten) wird zurückgegeben

Zusätzlich:
- `MixController.get_status()` liefert den gecachten Status aus dem Monitor

---

### `Controller/pump_controller.py`
**Aufgabe:** Use-Case „Kalibrierung / Setup mit Hardware“.  
**Outcome:** Startet gezielte Pumpenläufe, speichert Flow-Rate/Position in die DB, nutzt dabei die bestehende Maschinenlogik.

**Greift zu auf:**
- `Services/mix_engine.py` (Homing/Bewegung, geteilte Hardware-Instanz)
- `Services/pump_calibration_service.py` (Pumpen-Testlauf + busy-warten)
- `Model/pump_model.py` (Speichern/Laden der Pumpenparameter)

Wichtig: Der `PumpController` bekommt die bestehende `MixEngine`, damit es nur eine Hardware-/Monitor-Instanz gibt.

---

### `Controller/admin_controller.py`
**Aufgabe:** Use-Case „Datenpflege“.  
**Outcome:** Zutaten/Cocktails/Pumpen-Datensätze werden in SQLite verwaltet.

**Greift zu auf:**
- `Model/ingredient_model.py`
- `Model/cocktail_model.py`
- optional `Model/pump_model.py` (add/delete Pumpe, DB-Mapping)

Wichtig: Der `AdminController` braucht keine `MixEngine`, weil er keine Hardware bewegt.

---

## Services (Maschinenlogik und Ablauf)

### `Services/mix_engine.py`
**Aufgabe:** Maschinenabläufe sicher und sequenziell ausführen.  
**Outcome:** Führt Homing, Schlittenbewegung und Pumpen in definierter Reihenfolge aus. Wartet zwischen jedem Schritt, bis `busy=False`.

**Greift zu auf:**
- `Hardware/i2C_logic.py` (Kommandos senden)
- `Services/status_monitor.py` (Status-Caching + I2C-Exklusivität)
- `Services/status_service.py` (Statusinterpretation + wait_until_idle)

Wichtige Eigenschaften:
- Zwischen Schritten wird immer geprüft, dass die Maschine nicht busy ist
- Kommunikation läuft über `monitor.run_i2c(...)`, damit keine I2C-Kollisionen entstehen
- Simulation und echte Hardware laufen über dieselbe API

---

### `Services/pump_calibration_service.py`
**Aufgabe:** Pumpen-Testlauf für Kalibrierung, inklusive busy-warten.  
**Outcome:** Pumpe läuft kontrolliert für eine definierte Zeit, danach ist sicher wieder `busy=False`. Zusätzlich kann aus Messwerten `ml/s` berechnet werden.

**Greift zu auf:**
- `Services/status_monitor.py` (Command exklusiv senden)
- `Services/status_service.py` (busy-warten)

Typische Methoden:
- `run_pump_for_seconds(i2c, pump_number, seconds)`  
  wartet idle → sendet Pumpenkommando → wartet idle
- `calc_flow_rate_ml_s(measured_ml, seconds)`  
  berechnet `flow_rate_ml_s = measured_ml / seconds`

---

### `Services/status_monitor.py`
**Aufgabe:** Status im Hintergrund pollen und den letzten Status zwischenspeichern.  
**Outcome:** `get_latest()` liefert jederzeit den letzten bekannten Status, ohne direkten I2C-Zugriff im View.

Zusätzlich:
- `run_i2c(fn, *args)` pausiert Polling kurz und führt einen exklusiven I2C-Befehl aus  
  (verhindert gleichzeitiges Lesen/Schreiben auf dem Bus)

---

### `Services/status_service.py`
**Aufgabe:** Statuspaket (5 Bytes) interpretieren und Entscheidungshilfen liefern.  
**Outcome:** Liefert Status-Dict mit Feldern wie `busy`, `homing_ok`, `ist_position`, `ok`, `error_msg`.

Enthält außerdem:
- `wait_until_idle_cached(get_status_fn, timeout_s, poll_s)`  
  wartet, bis `busy=False` oder ein Fehler/Timeout eintritt

Statusformat (vom Arduino):
- Byte 0: `busy`
- Byte 1: `band_belegt`
- Byte 2-3: `ist_position` (int16)
- Byte 4: `homing_ok`

---

## Models (SQLite Zugriff)

### `Model/mix_model.py`
**Aufgabe:** Liefert die Mixdaten für einen Cocktail (Zutaten, Reihenfolge, Pumpendaten).  
**Outcome:** Liste von Datensätzen, die die MixEngine sequenziell abarbeitet.

Typisch: `JOIN` über `cocktails`, `cocktail_ingredients`, `ingredients`, `pumps`, sortiert nach `order_index`.

---

### `Model/pump_model.py`
**Aufgabe:** Pumpen-Konfiguration lesen und schreiben.  
**Outcome:** `flow_rate_ml_s`, `position_steps`, `ingredient_id` können ausgelesen und aktualisiert werden.

Typische Methoden:
- `get_all_pumps()`
- `update_flow_rate(pump_number, flow_rate_ml_s)`
- `update_position_steps(pump_number, steps)`
- `update_ingredient(pump_number, ingredient_id)`
- optional `add_pump(...)`, `delete_pump(...)`

---

### `Model/ingredient_model.py`
**Aufgabe:** CRUD für Zutaten (`ingredients`).  
**Outcome:** Zutaten können angezeigt, hinzugefügt, umbenannt, gelöscht werden.

---

### `Model/cocktail_model.py`
**Aufgabe:** CRUD für Cocktails (`cocktails`).  
**Outcome:** Cocktails können angezeigt, hinzugefügt, umbenannt, gelöscht werden.

---

## Hardware

### `Hardware/i2C_logic.py`
**Aufgabe:** I2C-Kommunikation zum Arduino (auch Simulation möglich).  
**Outcome:** Stellt Methoden bereit wie `home()`, `move_to_position(steps)`, `activate_pump(pump_id, seconds)`, `getstatus_raw()`.

Simulation:
- hält einen internen Simulationszustand (Position, busy, etc.)
- `getstatus_raw()` liefert ein passendes 5-Byte Statuspaket

---

## Beispielablauf: Flow-Rate Kalibrierung

Ziel: Pumpe läuft X Sekunden, gemessene ml werden eingegeben, `flow_rate_ml_s` wird in SQLite gespeichert.

1. User öffnet Kalibrierung im Hauptmenü  
   `ConsoleView` → `CalibrationView.run()`

2. User wählt „Flow-Rate kalibrieren“  
   `CalibrationView` fragt `pump_number` und `seconds` ab

3. Pumpenlauf starten  
   `CalibrationView` → `PumpController.run_pump_for_calibration(pump_number, seconds)`

4. Service führt den Pumpenlauf sicher aus  
   `PumpController` → `PumpCalibrationService.run_pump_for_seconds(i2c, pump_number, seconds)`  
   - wartet bis `busy=False`  
   - sendet Pumpenkommando exklusiv über `monitor.run_i2c(...)`  
   - wartet bis `busy=False`

5. User misst ml und gibt Wert ein  
   `CalibrationView` fragt `measured_ml`

6. Flow-Rate berechnen und speichern  
   `CalibrationView` → `PumpController.save_flow_rate_from_measurement(pump_number, measured_ml, seconds)`  
   - `PumpCalibrationService.calc_flow_rate_ml_s(measured_ml, seconds)`  
   - `PumpModel.update_flow_rate(pump_number, flow_rate_ml_s)`

Outcome: `flow_rate_ml_s` ist in SQLite aktualisiert und wird beim nächsten Mixvorgang für die Pumpzeitberechnung genutzt (`seconds = ml / flow_rate_ml_s`).

---

## Beispielablauf: Cocktail mischen

1. User wählt „Cocktail mischen“  
   `ConsoleView` → `CocktailView.run_mix_flow()`

2. Cocktail-ID eingeben und Mix starten  
   `CocktailView` → `MixController.mix_cocktail(cocktail_id)`

3. Rezeptdaten aus der DB lesen  
   `MixController` → `MixModel.get_full_mix_data(cocktail_id)`

4. Maschine führt Schritte sequenziell aus  
   `MixController` → `MixEngine.mix_cocktail(mix_data)`  
   - homing sicherstellen (falls nötig)  
   - pro Zutat: idle prüfen → zur Position fahren → idle prüfen → Pumpe starten → idle prüfen

Outcome: Cocktail wird in der vorgegebenen Reihenfolge gemischt, und Statusbits (busy/homing_ok/position) steuern das Fortschreiten im Ablauf.

# Vorteile einer MVC-Struktur (Model–View–Controller)

## 1) Klare Trennung von Verantwortlichkeiten
- **Model**: Datenhaltung und Datenlogik (z.B. SQLite-Zugriffe, CRUD)
- **View**: Benutzeroberfläche (Ein-/Ausgabe, Darstellung, GUI/Console)
- **Controller**: Steuert Anwendungsfälle (Use-Cases) und koordiniert Abläufe  
Outcome: Jede Datei hat einen klaren Zweck, Code wird leichter verständlich.

## 2) Bessere Wartbarkeit und weniger Chaos im Code
Wenn UI-Logik, Datenbankzugriffe und Hardwaresteuerung nicht vermischt sind, entstehen:
- weniger Seiteneffekte
- weniger „Spaghetti-Code“
- einfacheres Debugging  
Outcome: Änderungen lassen sich gezielter durchführen, ohne unbeabsichtigt andere Bereiche zu zerstören.

## 3) Austauschbare Benutzeroberfläche (Console → GUI → Web)
Wenn die View nur Controller-Methoden aufruft, kann man die Oberfläche später austauschen:
- Konsole heute
- GUI (z.B. Kivy) morgen
- Web-Frontend später  
Outcome: Die Logik bleibt gleich, nur die Darstellung ändert sich.

## 4) Bessere Testbarkeit
- Models lassen sich mit einer Test-DB testen
- Controller lassen sich testen, indem man Models/Services „mockt“
- Views enthalten möglichst wenig Logik und sind dadurch weniger fehleranfällig  
Outcome: Viele Fehler werden früh erkannt, ohne Hardware oder UI zu benötigen.

## 5) Wiederverwendbare Logik
Controller und Services können in mehreren Views genutzt werden:
- Kalibrierung (Console)
- Admin-Menü (Console)
- später dieselben Funktionen in GUI-Buttons/Forms  
Outcome: Keine doppelte Implementierung derselben Abläufe.

## 6) Teamarbeit wird einfacher
Bei mehreren Personen im Projekt kann man Aufgaben sauber trennen:
- Person A: Views / UI
- Person B: Controller / Use-Cases
- Person C: Model / Datenbank
- Person D: Services / Hardwarelogik  
Outcome: Weniger Konflikte im Code und klarere Schnittstellen.

## 7) Saubere Erweiterbarkeit (Skalierbarkeit)
Neue Funktionen können ergänzt werden, ohne das ganze System umzubauen:
- neue View/Untermenüs (Admin, Kalibrierung)
- neue Models (Ingredients, Cocktails, Rezepte)
- neue Controller (AdminController, PumpController)  
Outcome: Das Projekt wächst kontrolliert, statt unübersichtlich zu werden.

## 8) Bessere Dokumentierbarkeit
MVC bietet eine leicht erklärbare Struktur:
- „View zeigt an“
- „Controller steuert“
- „Model speichert“  
Outcome: Architektur lässt sich in einer Abschlussarbeit klar begründen und darstellen.

## 9) Weniger Risiko bei Änderungen (geringere Kopplung)
Ändert man z.B. das Datenbankschema, betrifft das primär das Model.  
Ändert man die UI, betrifft das primär die View.  
Outcome: Änderungen sind lokal begrenzt, die Wahrscheinlichkeit neuer Bugs sinkt.

## Fazit
MVC sorgt für eine strukturierte Codebasis, die leichter zu warten, zu testen und zu erweitern ist. Besonders bei Projekten mit Hardware und späterem GUI-/Web-Umstieg ist die Trennung von UI, Daten und Ablaufsteuerung ein großer Vorteil.
