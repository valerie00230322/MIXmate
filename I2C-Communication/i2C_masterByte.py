from smbus2 import SMBus
import time

# I2C-Adresse des Arduino-Slaves (muss auf beiden Seiten gleich sein)
ARDUINO_ADDR = 0x08  

bus = SMBus(1)  # I2C-Bus 1 = standard auf Raspberry Pi

def send_data(direction, hoehe, distanz):
    """
    direction: 0 = Links, 1 = Rechts
    hoehe/distanz: int (mm), 0-65535
    """
    # Bytes vorbereiten (wir senden 5 Bytes total)
    data = [
        direction & 0xFF,
        hoehe & 0xFF, (hoehe >> 8) & 0xFF,
        distanz & 0xFF, (distanz >> 8) & 0xFF
    ]
    
    # Daten senden
    bus.write_i2c_block_data(ARDUINO_ADDR, 0x00, data)
    print("Gesendet:", data)

# Beispielschleife
while True:
    send_data(1, 1234, 5678)  # Rechts, Höhe 1234mm, Distanz 5678mm
    time.sleep(1)
