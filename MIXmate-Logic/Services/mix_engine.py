# Services/mix_engine.py (oder wo deine MixEngine liegt)

from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor
import time


class MixEngine:
    HOME_TIMEOUT = 180
    MOVE_TIMEOUT = 180
    PUMP_TIMEOUT_EXTRA = 10
    HOME_POSITION_STEPS = 0

    # Wie lange wir nach Homing noch auf "homing_ok=True" warten,
    # damit der StatusMonitor garantiert aktualisiert hat:
    POST_HOME_STATUS_SYNC_TIMEOUT = 5.0

    def __init__(self, simulation: bool = False):
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

    # -------------------------
    # FIX #1: Robust auf idle warten (busy=False), NICHT auf ok=True
    # -------------------------
    def _wait_until_idle(self, timeout_s: float, context: str):
        """
        Robust: wartet primär auf busy=False.
        Hintergrund: dein StatusService setzt ok=False solange homing_ok=False
        und nach Homing kann der Monitor kurz stale sein -> ok bleibt kurz False.
        """
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            st = self.get_status()
            last = st

            if not self._busy(st):
                return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: Timeout. busy blieb True. Status={last}")

    def _wait_until_idle_allow_not_homed(self, timeout_s: float, context: str):
        """
        Beim Homing ist homing_ok möglicherweise noch False -> ok wäre dann False.
        Deshalb ebenfalls nur busy abwarten.
        """
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            st = self.get_status()
            last = st

            if not self._busy(st):
                return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: Timeout. busy blieb True. Status={last}")

    # -------------------------
    # FIX #2: Nach Homing aktiv auf homing_ok=True warten (Status-Sync)
    # -------------------------
    def _wait_for_homing_ok(self, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            st = self.get_status()
            last = st

            if (not self._busy(st)) and self._homing_ok(st):
                return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    def ensure_homed(self):
        st = self.get_status()

        homing_ok = self._homing_ok(st)
        pos = self._position(st)

        needs_home = (not homing_ok)
        if pos is not None and pos != self.HOME_POSITION_STEPS:
            needs_home = True

        if not needs_home:
            print("[MixEngine] Schlitten ist bereits gehomed")
            return

        print("[MixEngine] Schlitten ist nicht gehomed, starte Homing")

        # Vor Homing warten, bis nicht busy
        self._wait_until_idle_allow_not_homed(self.HOME_TIMEOUT, "Homing vor Start")

        # Homing ausführen
        self.monitor.run_i2c(self.i2c.home)

        # Warten bis Homing-Prozess fertig (busy=False)
        self._wait_until_idle_allow_not_homed(self.HOME_TIMEOUT, "Homing nach Start")

        # WICHTIG: Jetzt noch warten, bis der Monitor homing_ok wirklich auf True hat
        self._wait_for_homing_ok(self.POST_HOME_STATUS_SYNC_TIMEOUT, "Status-Sync nach Homing")

        print("[MixEngine] Homing abgeschlossen")

    def move_to_position(self, target_position: int):
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein")

        # robust warten (busy=False)
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

        # <- hier passiert dein Problem: wenn nicht gehomed, homing + stale status
        #    wird jetzt sauber abgefangen
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
