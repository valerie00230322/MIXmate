from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor
import time


class MixEngine:
    HOME_TIMEOUT = 180     # 3 Minuten
    MOVE_TIMEOUT = 180     # 3 Minuten
    HOME_POSITION_STEPS = 0  # ggf. anpassen, falls Home nicht 0 ist

    def __init__(self, simulation: bool = False):
        self.i2c = i2C_logic(simulation=simulation)
        self.status_service = StatusService()
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()

    def get_status(self):
        return self.monitor.get_latest()

    # ---- Helpers: busy aus Status lesen (robust gegen verschiedene Feldnamen) ----
    def _status_busy(self, status) -> bool:
        """
        Versucht 'busy' aus deinem Statusobjekt zu lesen.
        Passe hier an, falls dein Feld anders heißt.
        """
        if status is None:
            return False

        for name in ("busy", "is_busy", "motor_busy", "mixer_busy"):
            if hasattr(status, name):
                return bool(getattr(status, name))
            if isinstance(status, dict) and name in status:
                return bool(status[name])

        # Fallback: wenn kein busy-Feld vorhanden ist
        return False

    def _wait_until_idle(self, timeout_s: float) -> bool:
        return self.status_service.wait_until_idle_cached(
            self.monitor.get_latest,
            timeout_s=timeout_s,
            poll_s=0.2
        )

    def _wait_for_busy_then_idle(self, timeout_s: float, busy_start_grace_s: float = 2.0):
        """
        Robust gegen "busy wurde verpasst":
        - gibt kurz Zeit, dass busy=True auftaucht (grace)
        - wenn busy nie gesehen wird -> OK (kein sofortiger Timeout)
        - wenn busy gesehen wird -> wartet bis busy wieder False ist (bis timeout_s)
        """
        start = time.time()
        saw_busy = False

        grace_end = start + busy_start_grace_s
        while time.time() < grace_end:
            st = self.get_status()
            if self._status_busy(st):
                saw_busy = True
                break
            time.sleep(0.05)

        if not saw_busy:
            # Busy wurde evtl. zu kurz gesetzt oder vom Polling verpasst.
            # Nicht sofort scheitern.
            return

        if not self._wait_until_idle(timeout_s=timeout_s):
            raise RuntimeError("❌ Timeout: busy wurde nicht wieder False (idle) innerhalb des Limits.")

    # ---- Aktionen ----
    def home(self):
        print("[MixEngine] Starte Homing")
        self.monitor.run_i2c(self.i2c.home)

        # Homing kann länger dauern -> 3 Minuten, grace etwas größer
        self._wait_for_busy_then_idle(timeout_s=self.HOME_TIMEOUT, busy_start_grace_s=3.0)

        # Falls busy nie gesehen wurde, kann Homing trotzdem noch laufen.
        # Optional: zur Sicherheit immer noch auf idle warten (ohne busy-Start-Anforderung):
        if not self._wait_until_idle(timeout_s=self.HOME_TIMEOUT):
            raise RuntimeError("❌ Homing fehlgeschlagen (Timeout 3 Minuten).")

        print("[MixEngine] Homing abgeschlossen")

    def move_to_position(self, target_position: int):
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein.")

        current_position = self.i2c.get_current_position()
        print(f"[MixEngine] Bewege von {current_position} nach {target_position}")

        self.monitor.run_i2c(self.i2c.move_to_position, target_position)

        # Bewegung: nicht sofort failen wenn busy verpasst wird
        self._wait_for_busy_then_idle(timeout_s=self.MOVE_TIMEOUT, busy_start_grace_s=2.0)

        # Und trotzdem am Ende sicherstellen, dass es wirklich idle ist
        if not self._wait_until_idle(timeout_s=self.MOVE_TIMEOUT):
            raise RuntimeError(
                f"❌ Schlitten hat Position {target_position} "
                f"nicht innerhalb von 3 Minuten erreicht."
            )

        print("[MixEngine] Position erreicht")

    def _dispense(self, pump_number: int, seconds: int):
        print(f"[MixEngine] Starte Pumpe {pump_number} für {seconds}s")

        self.monitor.run_i2c(self.i2c.activate_pump, pump_number, seconds)

        # Pumpen sollte busy relativ sicher setzen, grace kleiner
        self._wait_for_busy_then_idle(timeout_s=seconds + 10, busy_start_grace_s=1.0)

        # Absichern: wirklich idle nach Pumpen
        if not self._wait_until_idle(timeout_s=seconds + 10):
            raise RuntimeError(f"❌ Pumpe {pump_number} hat nicht rechtzeitig beendet.")

        print(f"[MixEngine] Pumpe {pump_number} fertig")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten dürfen nicht leer sein.")

        # 1) Nur homen, wenn nicht auf Ausgangsposition
        try:
            current_position = self.i2c.get_current_position()
        except Exception:
            current_position = None

        if current_position is None or current_position != self.HOME_POSITION_STEPS:
            print(f"[MixEngine] Nicht auf Home-Position ({current_position}) -> Homing nötig")
            self.home()
        else:
            print("[MixEngine] Bereits auf Home-Position -> kein Homing nötig")

        # 2) Zutaten strikt nacheinander
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

            # a) zur Pumpenposition fahren + warten bis idle
            self.move_to_position(position_steps)

            # b) Pumpdauer berechnen (Arduino akzeptiert 1..255s)
            dispense_time_s = amount_ml / flow_rate
            seconds = max(1, min(255, int(round(dispense_time_s))))

            # c) pumpen + warten bis idle
            self._dispense(pump_number, seconds)

        print("[MixEngine] Cocktail fertig 🍹")
        return mix_data
