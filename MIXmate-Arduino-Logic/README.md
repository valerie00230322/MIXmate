# Hinzugefügte Funktionalitäten

> Das ist nur ein Entwurf, kommt drauf an, was Etti dazu sagt.

## Ultraschall SR04 

### Implementierung aktuell

Wenn ein Glas näher als *DISTANCE_THRESHOLD_CM* (5 cm) kommt, stoppt das Förderband. 

>// Sensor-Modus
>float dist = getDistance_cm();
>if (dist > 0 && dist <= DISTANCE_THRESHOLD_CM) {
>  activeBandTask.motor->stop();
>  activeBandTask.stopping = true;
>}

 --> Also eher Flas angekommen bzw. erkannt.

 **I2C Nachricht aktuell**

 >[busy, band, pos_low, pos_high, homing_ok]

 ### Neues Feature: Erkennen,ob sich das Glas verschiebt

 Ich würde gern ein Bit in die I2C-Message einfügen, welches Bescheid gibt, wenn sich das Glas verschiebt.
 Neues Feature beinhaltet folgendes:

     - Beim Beladen wird Referenzdistanz gespeichert - dann wird regelmäßig gemessen, ob sich Glas bewegt hat
     - Das bedeutet: zusätzliches Flag wird Implementiert --> Flag: Glas da / Glas verschoben

