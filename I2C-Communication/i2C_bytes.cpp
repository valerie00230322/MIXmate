#include <Wire.h>

void setup() {
  Serial.begin(9600);
  Wire.begin(0x08);  // gleiche Adresse wie beim Pi
  Wire.onReceive(receiveEvent);
}

void loop() {
  delay(10);  // kleine Pause
}

void receiveEvent(int numBytes) {
  if (numBytes == 6) {  
    Wire.read(); // Erstes Byte = Command -> ignorieren

    byte dir = Wire.read();
    byte h_low = Wire.read();
    byte h_high = Wire.read();
    byte d_low = Wire.read();
    byte d_high = Wire.read();

    int hoehe = (h_high << 8) | h_low;
    int distanz = (d_high << 8) | d_low;
    String richtung = (dir == 0) ? "Links" : "Rechts";

    Serial.print("Richtung: ");
    Serial.print(richtung);
    Serial.print(" | Höhe: ");
    Serial.print(hoehe);
    Serial.print(" mm | Distanz: ");
    Serial.print(distanz);
    Serial.println(" mm");
  } else {
    Serial.print("Falsche Anzahl Bytes: ");
    Serial.println(numBytes);
  }
}
