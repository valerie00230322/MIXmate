# Services/mix_engine.py

from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor
import time


class MixEngine:
    HOME_TIMEOUT = 180
    MOVE_TIMEOUT = 180
    PUMP_TIMEOUT_EXTRA = 10
    HOME_POSITION_UNITS = 0

    # nach einem Befehl warten wir kurz, bis busy im Status wirklich auf 1 springt
    BUSY_START_TIMEOUT = 2.0

    # nach Homing warten wir zusätzlich, bis homing_ok wirklich 1 ist
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

    # --------- Warten über echten I2C-Status statt Cache ---------

    def _refresh_status(self) -> dict:
        """
        Liest den Status einmal direkt über I2C (unter dem Monitor-Lock),
        aktualisiert damit implizit den internen Stand (weil parse im Monitor passiert),
        und liefert den frisch gelesenen Status zurück.

        Voraussetzung:
        StatusMonitor.get_latest() ist Cache-only. Deshalb holen wir hier den Status
        direkt über i2c und parsen ihn über StatusService.
        """
        raw = self.monitor.run_i2c(self.i2c.getstatus_raw)
        st = self.status_service.parse_status(raw)
        return st

    def _wait_until_idle(self, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if not self._busy(last):
                return
            time.sleep(0.2)

        raise RuntimeError(f"{context}: Timeout. busy blieb True. Status={last}")

    def _wait_until_busy(self, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if self._busy(last):
                return
            time.sleep(0.05)

        raise RuntimeError(f"{context}: Timeout. busy wurde nicht True. Status={last}")

    def _wait_until_idle_allow_not_homed(self, timeout_s: float, context: str):
        # identisch zu idle-wait, aber ohne homing_ok-Annahmen (wir prüfen nur busy)
        return self._wait_until_idle(timeout_s, context)

    def _wait_for_homing_ok(self, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if (not self._busy(last)) and self._homing_ok(last):
                return
            time.sleep(0.2)

        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    # --------- Logik ---------

    def ensure_homed(self):
        st = self._refresh_status()

        homing_ok = self._homing_ok(st)
        pos = self._position(st)

        needs_home = (not homing_ok)
        if pos is not None and pos != self.HOME_POSITION_UNITS:
            needs_home = True

        if not needs_home:
            print("[MixEngine] Schlitten ist bereits gehomed")
            return

        print("[MixEngine] Schlitten ist nicht gehomed, starte Homing")

        self._wait_until_idle_allow_not_homed(self.HOME_TIMEOUT, "Homing vor Start")

        # Homing anstoßen
        self.monitor.run_i2c(self.i2c.home)

        # warten bis Arduino das Kommando im loop() wirklich aufgenommen hat (busy=1)
        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Homing Start")

        # warten bis busy wieder 0
        self._wait_until_idle_allow_not_homed(self.HOME_TIMEOUT, "Homing nach Start")

        # warten bis homing_ok wirklich 1 ist
        self._wait_for_homing_ok(self.POST_HOME_STATUS_SYNC_TIMEOUT, "Status-Sync nach Homing")

        print("[MixEngine] Homing abgeschlossen")

    def move_to_position(self, target_position: int):
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein")

        self._wait_until_idle(self.MOVE_TIMEOUT, "Bewegung vor Start")

        st = self._refresh_status()
        print(f"[MixEngine] Fahre Schlitten von {self._position(st)} nach {target_position}")

        self.monitor.run_i2c(self.i2c.move_to_position, target_position)

        # Start-Handshake: busy muss erst 1 werden, sonst ist Status evtl. noch alt
        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Bewegung Start")

        self._wait_until_idle(self.MOVE_TIMEOUT, "Bewegung nach Start")
        print("[MixEngine] Position erreicht")

    def _dispense(self, pump_number: int, seconds: int):
        timeout = seconds + self.PUMP_TIMEOUT_EXTRA

        self._wait_until_idle(timeout, "Pumpen vor Start")

        print(f"[MixEngine] Starte Pumpe {pump_number} für {seconds} Sekunden")
        self.monitor.run_i2c(self.i2c.activate_pump, pump_number, seconds)

        # Start-Handshake
        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Pumpen Start")

        self._wait_until_idle(timeout, "Pumpen nach Start")
        print(f"[MixEngine] Pumpe {pump_number} beendet")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten sind leer")

        # Reihenfolge prüfen
        # (Wenn hier Mist rauskommt, ist es ein DB-Problem, nicht MixEngine.)
        order_list = [(x.get("order_index"), x.get("ingredient_name")) for x in mix_data]
        print("[MixEngine] Reihenfolge:", order_list)

        self.ensure_homed()

        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = float(item["amount_ml"]) * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position = item["position_steps"]  # Achtung: bei euch evtl. Units, nicht Steps

            if pump_number is None or flow_rate is None or flow_rate <= 0:
                print(f"[MixEngine] {ingredient}: ungültige Pumpendaten, übersprungen")
                continue

            # 1) zuerst zur Zutat fahren (und warten bis fertig)
            print(f"[MixEngine] Fahre zu {ingredient} (Pumpe {pump_number})")
            self.move_to_position(position)

            # 2) dann pumpe laufen lassen (und warten bis fertig)
            dispense_time_s = amount_ml / flow_rate
            seconds = max(1, min(255, int(round(dispense_time_s))))

            print(f"[MixEngine] Pumpe {pump_number}: {amount_ml:.1f} ml -> {seconds}s")
            self._dispense(pump_number, seconds)

        print("[MixEngine] Cocktail vollständig gemixt")
        return mix_data
