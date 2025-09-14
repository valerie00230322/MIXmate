import smbus
import time

# I2C Bus
bus = smbus.SMBus(1)
SLAVE_ADDRESS = 0x04

# Status-Definitionen
STATUS = {
    0: "BEREIT",
    1: "FAHREND",
    2: "ANGEKOMMEN",
    3: "FEHLER"
}

def send_pumpe_command(pumpe_nr):
    """Sendet Befehl zum Fahren einer Pumpe"""
    try:
        bus.write_byte(SLAVE_ADDRESS, pumpe_nr)
        print(f"Pumpe {pumpe_nr} losgeschickt")
    except Exception as e:
        print(f"Fehler beim Senden: {e}")

def get_pumpen_status():
    """Holt Status aller Pumpen"""
    try:
        # Liest 5 Byte für 5 Pumpen
        status_array = bus.read_i2c_block_data(SLAVE_ADDRESS, 0, 5)
        
        # Ausgabe des Status
        for i, status in enumerate(status_array, 1):
            print(f"Pumpe {i}: {STATUS.get(status, 'UNBEKANNT')}")
        
        return status_array
    except Exception as e:
        print(f"Fehler beim Empfangen: {e}")
        return None

def warte_auf_pumpe(pumpe_nr):
    """Wartet, bis eine bestimmte Pumpe angekommen ist"""
    while True:
        status = get_pumpen_status()
        if status and status[pumpe_nr-1] == 2:  # ANGEKOMMEN
            print(f"Pumpe {pumpe_nr} ist angekommen!")
            break
        time.sleep(0.5)

# Hauptprogramm
try:
    while True:
        # Benutzer-Eingabe
        pumpe = int(input("Welche Pumpe soll fahren? (1-5): "))
        
        # Pumpe losschicken
        send_pumpe_command(pumpe)
        
        # Auf Ankunft warten
        warte_auf_pumpe(pumpe)
        
        time.sleep(1)

except KeyboardInterrupt:
    print("Programm beendet")