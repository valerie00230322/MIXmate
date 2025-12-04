# MIXmate Dokumentation

## Ablauf

1. Cocktail wird ausgewählt 
2. Über Datenbank werden die Zutaten ausgelesen
3. Aus der Datenbank wird sowohl die Pumpenzuordnung für die einzelnen Zutaten als auch die Kalibrierung der Pumpen ausgelesen. Die Kalibrierung der Pumpen enthält, wie viel Flüssigkeit die Pumpe pro Sekunde hinauspumpt.
5. Für die Pumpe der ersten Zutat wird der Abstand aus der Datenbank geladen, um dies dem Arduino über I2C weiterzugeben
6. Es wird immer wieder über I2C der Status des Schlittens abgefragt
7. Senden der Zeit und der Pumpennummer für die erste Zutat über I2C
8. danach kommt die nächste Zutat und es wird für diese Schritt 3-7 wiederholt

## Statuscodes

Bei jeder Statusabfrage - **CMD_STATUS = 2** - I2C bekommt man folgende Nachrichten:
Statusabfrage hat 5 Bytes.

- _busy_: Mixer bzw. Pumpe ist gerade beschäftigt (1 Byte)
- _Belegung Förderband_: Glas ist auf Förderband. Auch wenn ich vor Pumpe stehe, kontrollieren, ob Glas noch auf Förderband ist(1 Byte)
- _Ist-Position Schlitten_: Wo fährt Schlitten zu Pumpe --> Überprüfung,ist und soll Position von Schlitten (2 Bytes)
- _Homeing_: OK or NOK --> Abfrage, ob Schlitten gehomed ist. Bei jedem neuen Getränk nachfragen, ob Schlitten gehomed ist (1 Byte)


### Fehlercodes und Fehlerfälle

- _Kollisionserkennung_: Schlitten erkennt Kollision 
- _Pumpe steckt_
- _Glas heruntergefallen_
- _Schlitten klemmt_
- _evtl. Flasche ist leer_

## MVC Ablauf

MIXmate/
│
├── app.py                          # Startpunkt des Programms
│
├── View/
│   └── console_view.py             # CLI oder GUI-View
│
├── Controller/
│   └── mix_controller.py           # Koordiniert Mix-Vorgang + Statusabfragen
│
├── Services/                       # Business-Logic (= dein "Logic"-Ordner)
│   ├── mix_engine.py               # enthält die Mix-Algorithmen
│   ├── status_service.py           # verwaltet Status der Maschine
│   └── recipe_service.py           # lädt/validiert Rezepte
│
├── Hardware/                       # direkte Hardware-Ansteuerung
│   ├── i2c_adapter.py              # Low-Level I2C Zugriff
│   └── pump_driver.py              # Pumpensteuerung (ruft I2C an)
│
├── Model/
│   ├── cocktail.py                 # Cocktail-Datenmodell
│   ├── ingredient.py               # Zutatenmodell
│   └── database.py                 # Datenbankzugriff (SQLite etc.)
│
└── Database/
    └── mixmate.db                  # tatsächliche SQLite-DB


![alt text](image.png)