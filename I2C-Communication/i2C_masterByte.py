from smbus2 import SMBus, i2c_msg

ARDUINO_ADDR = 0x08
bus = SMBus(1)

def send_data(direction, hoehe, distanz):
    data = [
        direction & 0xFF,
        hoehe & 0xFF, (hoehe >> 8) & 0xFF,
        distanz & 0xFF, (distanz >> 8) & 0xFF
    ]
    msg = i2c_msg.write(ARDUINO_ADDR, data)
    bus.i2c_rdwr(msg)
    print("Gesendet:", data)

send_data(1, 1234, 5678)
