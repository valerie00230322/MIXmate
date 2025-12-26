from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor


class MixEngine:
    HOME_TIMEOUT = 180
    MOVE_TIMEOUT = 180
    PUMP_TIMEOUT_EXTRA = 10
    HOME_POSITION_STEPS = 0

    def __init__(self, simulation: bool = False):
        # Debug: zeigt dir beim Start exakt, welche Datei geladen wird
        # print("LOADED MIXENGINE FILE:", __file__)

        self.i2c = i2C_logic(simulation=simulation)
        self.status_service = StatusService()
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()

    def get_status(self) -> dict:
        return self.monitor.get_latest()

    def _busy(self, status: dict) -> bool:
        return bool((status or {}).get("busy", False))

    def _homing_ok(self, status: dict) -> bool:
        return bool((status or {}).get("homing_ok", False))

    def _position(self, status: dict):
        return (status or {}).get("ist_position", None)

    def _wait_until_idle(self, timeout_s: float, context: str):
        ok = self.status_service.wait_until_idle_cached(
            self.monitor.get_latest,
            timeout_s=timeout_s,
            poll_s=0.2
        )
        if not ok:
            raise RuntimeError(f"{context}: busy blieb True oder ok=False. Status={self.get_status()}")

    def ensure_homed(self):
        st = self.get_status()

        # Debug falls du sehen willst, was wirklich ankommt:
        # print("STATUS:", st)

        homing_ok = self._homing_ok(st)
        pos = self._position(st)

        needs_home = (not homing_ok)
        if pos is not None and pos != self.HOME_POSITION_STEPS:
            needs_home = True

        if not needs_home:
            print("[MixEngine] Schlitten ist bereits gehomed")
            return

        print("[MixEngine] Schlitten ist nicht gehomed, starte Homing")

        # Vor dem Homing warten wir, bis nichts mehr busy ist.
        # Achtung: Dein StatusService markiert NOT_HOMED als ok=False.
        # Deshalb kann wait_until_idle_cached hier sofort False liefern.
        # Wir lösen das, indem wir beim Homing direkt über raw status gehen.
        self._wait_until_idle_allow_not_homed(self.HOME_TIMEOUT, "Homing vor Start")

        self.monitor.run_i2c(self.i2c.home)

        self._wait_until_idle_allow_not_homed(self.HOME_TIMEOUT, "Homing nach Start")

        st_after = self.get_status()
        if not self._homing_ok(st_after):
            raise RuntimeError(f"Homing wurde ausgeführt, aber homing_ok ist weiterhin 0. Status={st_after}")

        print("[MixEngine] Homing abgeschlossen")

    def _wait_until_idle_allow_not_homed(self, timeout_s: float, context: str):
        """
        Dein StatusService setzt ok=False solange homing_ok=False.
        Beim Homing ist das aber normal.
        Deshalb warten wir hier "nur" darauf, dass busy=False wird.
        """
        import time
        start = time.time()

        while time.time() - start < timeout_s:
            st = self.get_status()

            # Wenn busy False ist, ist der Schritt abgeschlossen
            if not self._busy(st):
                return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: busy blieb True (Timeout). Status={self.get_status()}")

    def move_to_position(self, target_position: int):
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein")

        self._wait_until_idle(self.MOVE_TIMEOUT, "Bewegung vor Start")

        st = self.get_status()
        print(f"[MixEngine] Fahre Schlitten von {self._position(st)} nach {target_position}")

        self.monitor.run_i2c(self.i2c.move_to_position, target_position)

        self._wait_until_idle(self.MOVE_TIMEOUT, "Bewegung nach Start")
        print("[MixEngine] Position erreicht")

    def _dispense(self, pump_number: int, seconds: int):
        timeout = seconds + self.PUMP_TIMEOUT_EXTRA

        self._wait_until_idle(timeout, "Pumpen vor Start")

        print(f"[MixEngine] Starte Pumpe {pump_number} für {seconds} Sekunden")
        self.monitor.run_i2c(self.i2c.activate_pump, pump_number, seconds)

        self._wait_until_idle(timeout, "Pumpen nach Start")
        print(f"[MixEngine] Pumpe {pump_number} beendet")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten sind leer")

        self.ensure_homed()

        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = item["amount_ml"] * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_steps = item["position_steps"]

            if pump_number is None or flow_rate is None or flow_rate <= 0:
                print(f"[MixEngine] {ingredient}: ungültige Pumpendaten, übersprungen")
                continue

            print(f"[MixEngine] Verarbeite {ingredient}: {amount_ml:.1f} ml")

            self.move_to_position(position_steps)

            dispense_time_s = amount_ml / flow_rate
            seconds = max(1, min(255, int(round(dispense_time_s))))

            self._dispense(pump_number, seconds)

        print("[MixEngine] Cocktail vollständig gemixt")
        return mix_data
