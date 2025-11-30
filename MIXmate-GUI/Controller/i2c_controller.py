import time

from smbus2 import SMBus, i2c_msg 

SIMULATION_MODE = True  # Set to False to use real I2C communication
I2C_BUS = 1       # Typically 1 on Raspberry Pi
I2C_ADDR = 0x13   # slave address
CMD_FAHR     = 0
CMD_HOME     = 1
CMD_PUMPE    = 3

def log(msg):
    print(f"[SIM] {msg}" if SIMULATION_MODE else msg) # Ausgabe-->logging

def pump(pump_id, time_s):
    if SIMULATION_MODE:
        log(f"STARTE PUMPE {pump_id} für {time_s:.2f} Sekunden...")
        time.sleep(min(time_s, 0.2))   # kurz warten (kein echtes 10s warten)
        log(f"PUMPE {pump_id} fertig.")
        return b"\x01"  # ACK-Simulation
    else:
        payload = bytes([CMD_PUMPE, pump_id & 0xFF, int(time_s) & 0xFF])
        with SMBus(I2C_BUS) as bus:
            write = i2c_msg.write(I2C_ADDR, payload)
            read  = i2c_msg.read(I2C_ADDR, 1)
            bus.i2c_rdwr(write, read)
            return bytes(read)

# Schlitten zu best. Pos.
def move_to(position_steps):
    if SIMULATION_MODE:
        log(f"FAHRE ZU POSITION {position_steps} Steps...")
        time.sleep(0.1)
        log(f"POSITION {position_steps} erreicht.")
        return b"\x01"
    else:
        steps = position_steps.to_bytes(4, "little", signed=True)
        payload = bytes([CMD_FAHR]) + steps
        with SMBus(I2C_BUS) as bus:
            write = i2c_msg.write(I2C_ADDR, payload)
            read  = i2c_msg.read(I2C_ADDR, 1)
            bus.i2c_rdwr(write, read)
            return bytes(read)