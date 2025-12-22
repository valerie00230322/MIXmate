from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor


class MixEngine:
    HOME_TIMEOUT = 180     # 3 Minuten
    MOVE_TIMEOUT = 180     # 3 Minuten

    def __init__(self, simulation: bool = False):
        self.i2c = i2C_logic(simulation=simulation)
        self.status_service = StatusService()
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()

    def get_status(self):
        return self.monitor.get_latest()

    def _wait_until_idle(self, timeout_s: float) -> bool:
        return self.status_service.wait_until_idle_cached(
            self.monitor.get_latest,
            timeout_s=timeout_s,
            poll_s=0.2
        )

    def home(self):
        print("[MixEngine] Starte Homing")

        self.monitor.run_i2c(self.i2c.home)

        if not self._wait_until_idle(timeout_s=self.HOME_TIMEOUT):
            raise RuntimeError("❌ Homing fehlgeschlagen (Timeout 3 Minuten).")

        print("[MixEngine] Homing abgeschlossen")

    def move_to_position(self, target_position: int):
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein.")

        current_position = self.i2c.get_current_position()
        print(f"[MixEngine] Bewege von {current_position} nach {target_position}")

        self.monitor.run_i2c(self.i2c.move_to_position, target_position)

        if not self._wait_until_idle(timeout_s=self.MOVE_TIMEOUT):
            raise RuntimeError(
                f"❌ Schlitten hat Position {target_position} "
                f"nicht innerhalb von 3 Minuten erreicht."
            )

        print("[MixEngine] Position erreicht")

    def _dispense(self, pump_number: int, seconds: int):
        print(f"[MixEngine] Starte Pumpe {pump_number} für {seconds}s")

        self.monitor.run_i2c(self.i2c.activate_pump, pump_number, seconds)

        if not self._wait_until_idle(timeout_s=seconds + 5):
            raise RuntimeError(
                f"❌ Pumpe {pump_number} hat nicht rechtzeitig beendet."
            )

        print(f"[MixEngine] Pumpe {pump_number} fertig")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten dürfen nicht leer sein.")

        # 1️⃣ Immer zuerst HOME
        #self.home()
#TODO: zuerst homen, dann warten bsis idle, danndistanz zu ersten Pumpe schicken,dann ml an Pumpe schicken, dann an zweite pumpe fahren, usw (immer zwischen operationen status abfragen und dann in den nächsten schritt gehen)
# immer nur homen weenn der schlitten nicht auf der ausgangsposition ist
        # 2️⃣ Zutaten strikt nacheinander
        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = item["amount_ml"] * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_steps = item["position_steps"]

            if pump_number is None or flow_rate is None or flow_rate <= 0:
                print(f"[MixEngine] {ingredient} hat keine gültige Pumpe – übersprungen.")
                continue

            print(f"[MixEngine] {ingredient}: {amount_ml:.1f} ml")

            # ➜ Schlitten fahren (3-Min-Timeout)
            self.move_to_position(position_steps)

            # ➜ Pumpdauer berechnen
            dispense_time_s = amount_ml / flow_rate
            seconds = max(1, min(255, int(round(dispense_time_s))))

            # ➜ Pumpen + warten
            self._dispense(pump_number, seconds)

        print("[MixEngine] Cocktail fertig 🍹")
        return mix_data
