# MIXmate Dokumentation

## Ablauf

1. Cocktail wird ausgewählt 
2. Über Datenbank werden die Zutaten ausgelesen
3. Aus der Datenbank wird sowohl die Pumpenzuordnung für die einzelnen Zutaten als auch die Kalibrierung der Pumpen ausgelesen. Die Kalibrierung der Pumpen enthält, wie viel Flüssigkeit die Pumpe pro Sekunde hinauspumpt.
4. Berechnunung der Zeit und mitgabe an Arduino welche Pumpe ausgewählt werden muss
5. Für die Pumpe der ersten Zutat wird der Abstand aus der Datenbank geladen, um dies dem Arduino über I2C weiterzugeben
6. Es wird immer wieder über I2C der Status des Schlittens abgefragt
7. Senden der Zeit und der Pumpennummer für die erste Zutat über I2C
8. danach kommt die nächste Zutat un es wird für diese Schritt 3-7 wiederholt

![alt text](image.png)