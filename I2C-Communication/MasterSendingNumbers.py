import smbus
import time

# I2C Bus (1 für neuere Raspberry Pi Modelle)
bus = smbus.SMBus(1)

# Slave-Adresse
SLAVE_ADDRESS = 0x04

def send_number(number):
    try:
        bus.write_byte(SLAVE_ADDRESS, number)
        print(f"Gesendet: {number}")
    except Exception as e:
        print(f"Fehler beim Senden: {e}")

# Hauptprogramm
try:
    while True:
        # Zahl vom Benutzer eingeben
        number = int(input("Zahl senden (0-255): "))
        
        # Zahl an Arduino senden
        send_number(number)
        
        # Kleine Pause
        time.sleep(1)

except KeyboardInterrupt:
    print("Programm beendet")
except ValueError:
    print("Ungültige Eingabe")