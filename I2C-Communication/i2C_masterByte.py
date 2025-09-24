from smbus2 import SMBus

ARDUINO_ADDR = 0x08  # gleiche Adresse wie im Arduino
bus = SMBus(1)       # I²C-Bus 1

def send_data(direction, hoehe, distanz):
    """
    direction: 0 = Links, 1 = Rechts
    hoehe/distanz: int (0-65535)
    """
    # Daten vorbereiten
    data = [
        direction & 0xFF,
        hoehe & 0xFF, (hoehe >> 8) & 0xFF,
        distanz & 0xFF, (distanz >> 8) & 0xFF
    ]
    
    # 0x01 = Dummy-Command-Byte
    bus.write_i2c_block_data(ARDUINO_ADDR, 0x01, data)
    print("Gesendet:", [0x01] + data)

# Beispiel: Rechts, Höhe 1234mm, Distanz 5678mm
send_data(1, 1234, 5678)
