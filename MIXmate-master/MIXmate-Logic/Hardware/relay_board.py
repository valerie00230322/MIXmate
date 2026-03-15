from gpiozero import OutputDevice

class RelayBoard:
    def __init__(self, pins: list[int], active_low: bool = True):
        self._relays = {
            pin: OutputDevice(pin, active_high=not active_low, initial_value=False)
            for pin in pins
        }

    def on(self, pin: int) -> None:
        self._relays[pin].on()

    def off(self, pin: int) -> None:
        self._relays[pin].off()

    def set_many(self, pins: list[int], state_on: bool) -> None:
        for pin in pins:
            self.on(pin) if state_on else self.off(pin)


    def all_off(self) -> None:
        for relay in self._relays.values():
            relay.off()

#python3 -c "import gpiozero; print('gpiozero ok', gpiozero.__version__)"
# wenn nicht installiert:
#sudo apt update
#sudo apt install -y python3-gpiozero
# oder sudo apt install -y python3-lgpio
