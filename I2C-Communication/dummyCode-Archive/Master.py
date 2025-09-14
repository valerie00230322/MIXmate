import smbus
import time

# I2C-Bus öffnen (Bus 1 ist Standard auf Raspberry Pi)
bus = smbus.SMBus(1)
addr = 0x12   # Adresse vom Arduino-Slave

print("I2C-Chat mit Arduino (Adresse 0x12)")
print("Tippe eine Nachricht und drücke Enter (exit zum Beenden)")

while True:
    msg = input("> ")
    if msg.lower() == "exit":
        break
    
    # In Bytes umwandeln
    data = [ord(c) for c in msg]
    
    try:
        # Nachricht senden: erstes Byte ist Register (z. B. 0x00), danach Daten
        bus.write_i2c_block_data(addr, 0x00, data)
        print("Gesendet:", msg)
    except Exception as e:
        print("Fehler beim Senden:", e)
    
    time.sleep(0.1)
