from gpiozero import OutputDevice

class RelayBoard:
    def __init__(self, pins: list[int], active_low: bool = True):
        self._relays = {
            pin: OutputDevice(pin, active_high=not active_low, initial_value=False)  # False => AUS
            for pin in pins
        }

    def on(self, pin: int) -> None:
        self._relays[pin].on()

    def off(self, pin: int) -> None:
        self._relays[pin].off()

    def set_many(self, pins: list[int], state_on: bool) -> None:
        for pin in pins:
            if state_on:
                self.on(pin)
            else:
                self.off(pin)

    def all_off(self) -> None:
        for relay in self._relays.values():
            relay.off()