# Services/mix_engine.py
#
# Ablauf:
# - StatusMonitor pollt regelmaessig den Arduino-Status, um I2C-Kollisionen zu vermeiden.
# - ensure_homed() stellt sicher, dass der Arduino eine gueltige Referenz hat (homing_ok == True).
# - Homing bedeutet: Positionsreferenz ist bekannt, nicht: Schlitten steht auf einer Zielposition.
# - move_to_position() faehrt den Schlitten auf eine Zielposition.
# - _dispense() steuert eine Pumpe fuer eine berechnete Zeitdauer an.
# - mix_cocktail() fuehrt die Rezeptschritte sequentiell aus.

import time

from Hardware.i2C_logic import i2C_logic
from Hardware.regal_i2c_logic import RegalI2CLogic
from Model.system_settings_model import SystemSettingsModel
from Services.simulation_trace_service import get_simulation_trace_service
from Services.status_monitor import StatusMonitor
from Services.status_service import StatusService


class MixEngine:
    HOME_TIMEOUT = 1800
    MOVE_TIMEOUT = 1800
    PUMP_TIMEOUT_EXTRA = 1000

    BUSY_START_TIMEOUT = 1800
    POST_HOME_STATUS_SYNC_TIMEOUT = 180
    POSITION_TOL_MM = 0
    REGAL_MOVE_TIMEOUT = 120.0
    REGAL_AUSSCHUB_TIMEOUT = 120.0
    REGAL_HOME_TIMEOUT = 180.0
    REGAL_GLASS_WAIT_TIMEOUT = 180.0
    MIXER_GLASS_WAIT_TIMEOUT = 60.0

    def __init__(self):
        self.i2c = i2C_logic()
        self.status_service = StatusService()
        # Hintergrund-Poller: hält den letzten Status bereit und serialisiert I2C-Zugriffe.
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()
        self.regal = self._init_regal()
        self.sim_trace = get_simulation_trace_service()
        self._sim_position_mm = 0
        self._sim_homed = False

    def _init_regal(self):
        try:
            regal = RegalI2CLogic()
            # Einmal Status lesen: so erkennen wir früh, ob der zweite Controller antwortet.
            raw = regal.get_status_raw()
            if len(raw) == 5:
                print("[MixEngine] Regal-Controller erkannt (I2C 0x12)")
                return regal
            regal.close()
        except Exception as e:
            print(f"[MixEngine] Regal-Controller nicht erkannt: {e}")
        return None

    def has_regal_controller(self) -> bool:
        if self.is_simulation_mode():
            return True
        if self.regal is None:
            return False
        st = self.regal.get_status()
        return bool(st.get("ok", False))

    def get_regal_status(self) -> dict:
        if self.is_simulation_mode():
            return {
                "ok": True,
                "connected": True,
                "busy": False,
                "band_belegt": True,
                "lift_sensor_belegt": True,
                "wait_start_belegt": False,
                "wait_end_belegt": False,
                "level1_front_belegt": True,
                "level2_front_belegt": True,
                "mixer_belegt": True,
                "entladen_blocked": False,
                "ist_position": int(self._sim_position_mm),
                "homing_ok": bool(self._sim_homed),
                "error_msg": "SIMULATION_MODE",
            }
        if self.regal is None:
            return {
                "ok": False,
                "connected": False,
                "error_code": "REGAL_NOT_CONNECTED",
                "error_msg": "Kein Regal-Controller an I2C 0x12 erkannt.",
            }
        st = self.regal.get_status()
        st["connected"] = bool(st.get("ok", False))
        return st

    def get_status(self) -> dict:
        if self.is_simulation_mode():
            status = self._sim_status()
        else:
            status = dict(self.monitor.get_latest() or {})
        regal_status = self.get_regal_status()
        status["regal_connected"] = bool(regal_status.get("connected", False))
        status["regal_ok"] = bool(regal_status.get("ok", False))
        status["regal_busy"] = regal_status.get("busy", False)
        status["regal_band_belegt"] = regal_status.get("band_belegt", False)
        status["regal_lift_sensor_belegt"] = regal_status.get("lift_sensor_belegt", False)
        status["regal_wait_start_belegt"] = regal_status.get("wait_start_belegt", False)
        status["regal_wait_end_belegt"] = regal_status.get("wait_end_belegt", False)
        status["regal_level1_front_belegt"] = regal_status.get("level1_front_belegt", False)
        status["regal_level2_front_belegt"] = regal_status.get("level2_front_belegt", False)
        # Mixer-Sensor liegt am Mixer-Controller (I2C 0x13), nicht am Regal.
        status["regal_mixer_belegt"] = bool(status.get("band_belegt", False))
        status["regal_entladen_blocked"] = regal_status.get("entladen_blocked", False)
        status["regal_ist_position"] = regal_status.get("ist_position", None)
        status["regal_homing_ok"] = regal_status.get("homing_ok", False)
        status["regal_error_msg"] = regal_status.get("error_msg", None)
        return status

    def is_simulation_mode(self) -> bool:
        settings = SystemSettingsModel()
        try:
            return bool(settings.get_simulation_mode())
        except Exception:
            return False
        finally:
            settings.close()

    def _sim_status(self) -> dict:
        return {
            "ok": True,
            "severity": "OK",
            "error_code": None,
            "error_msg": "SIMULATION_MODE",
            "busy": False,
            "band_belegt": True,
            "ist_position": int(self._sim_position_mm),
            "homing_ok": bool(self._sim_homed),
            "raw": b"",
        }

    def _sim_log_mixer(self, payload: list[int], note: str = ""):
        self.sim_trace.log_i2c(0x13, payload, note=note)

    def _sim_log_regal(self, payload: list[int], note: str = ""):
        self.sim_trace.log_i2c(0x12, payload, note=note)

    def _busy(self, status: dict) -> bool:
        return bool((status or {}).get("busy", False))

    def _homing_ok(self, status: dict) -> bool:
        return bool((status or {}).get("homing_ok", False))

    def _position_mm(self, status: dict):
        return (status or {}).get("ist_position", None)

    def _refresh_status(self) -> dict:
        if self.is_simulation_mode():
            return self._sim_status()
        # Exklusiv lesen, damit Polling und aktive Kommandos sich nicht ins Gehege kommen.
        raw = self.monitor.run_i2c(self.i2c.getstatus_raw)
        return self.status_service.parse_status(raw)

    def _wait_until_idle(self, timeout_s: float, context: str):
        # Zentraler Safety-Wait: viele Schritte dürfen nur im Idle starten.
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Ungueltiger Status (ok=False). Status={last}")
            if last.get("busy") is False:
                return
            time.sleep(0.2)

        raise RuntimeError(f"{context}: Timeout. busy blieb True. Status={last}")

    def _wait_for_homing_ok(self, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if (not self._busy(last)) and self._homing_ok(last):
                return
            time.sleep(0.2)

        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    def _wait_until_position_reached(self, target_mm: int, timeout_s: float, context: str, tol_mm: int = 0):
        start = time.time()
        last = None
        target_mm = int(target_mm)
        tol_mm = int(tol_mm)

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            pos = self._position_mm(last)

            if pos is not None:
                try:
                    pos_i = int(pos)
                except Exception:
                    pos_i = None

                if pos_i is not None and abs(pos_i - target_mm) <= tol_mm and (not self._busy(last)):
                    return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: Zielposition nicht erreicht. target_mm={target_mm}, Status={last}")

    def _wait_move_started(self, old_pos_mm: int, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if self._busy(last):
                return

            pos = self._position_mm(last)
            if pos is not None and old_pos_mm is not None:
                try:
                    if int(pos) != int(old_pos_mm):
                        return
                except Exception:
                    pass

            time.sleep(0.05)

        raise RuntimeError(f"{context}: Bewegung hat nicht gestartet. Status={last}")

    def _wait_pump_started(self, timeout_s: float, context: str):
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if self._busy(last):
                return
            time.sleep(0.05)

        raise RuntimeError(f"{context}: Pumpe hat nicht gestartet. Status={last}")

    def ensure_homed(self):
        if self.is_simulation_mode():
            if self._sim_homed:
                self.sim_trace.log_text("[SIM] Homing uebersprungen (bereits gehomed)")
                return
            self._sim_log_mixer([1], note="CMD_HOME")
            self._sim_homed = True
            self._sim_position_mm = 0
            self.sim_trace.log_text("[SIM] Homing abgeschlossen")
            return

        st = self._refresh_status()
        homing_ok = self._homing_ok(st)

        if homing_ok:
            print("[MixEngine] Schlitten ist bereits gehomed")
            return

        print("[MixEngine] Schlitten ist nicht gehomed, starte Homing")

        self._wait_until_idle(self.HOME_TIMEOUT, "Homing vor Start")

        old_pos = self._position_mm(self._refresh_status())
        # Kommando über den Monitor schicken, damit der Bus exklusiv genutzt wird.
        self.monitor.run_i2c(self.i2c.home)

        self._wait_move_started(old_pos, self.BUSY_START_TIMEOUT, "Homing Start")
        self._wait_until_idle(self.HOME_TIMEOUT, "Homing nach Start")
        self._wait_for_homing_ok(self.POST_HOME_STATUS_SYNC_TIMEOUT, "Status-Sync nach Homing")

        print("[MixEngine] Homing abgeschlossen")

    def move_to_position(self, target_mm: int):
        if target_mm is None:
            raise ValueError("Zielposition darf nicht None sein")

        target_mm = int(target_mm)
        if self.is_simulation_mode():
            low = target_mm & 0xFF
            high = (target_mm >> 8) & 0xFF
            self._sim_log_mixer([0, low, high], note=f"CMD_FAHR -> {target_mm} mm")
            self._sim_position_mm = target_mm
            self.sim_trace.log_text(f"[SIM] Position gesetzt auf {target_mm} mm")
            return

        self._wait_until_idle(self.MOVE_TIMEOUT, "Bewegung vor Start")

        st = self._refresh_status()
        old_pos = self._position_mm(st)

        if old_pos is not None:
            try:
                old_pos_i = int(old_pos)
            except Exception:
                old_pos_i = None

            if old_pos_i is not None and abs(old_pos_i - target_mm) <= self.POSITION_TOL_MM:
                print(f"[MixEngine] Zielposition {target_mm} bereits erreicht, Bewegung wird uebersprungen")
                return

        print(f"[MixEngine] Fahre Schlitten von {old_pos} nach {target_mm}")

        self.monitor.run_i2c(self.i2c.move_to_position, target_mm)

        self._wait_move_started(old_pos, self.BUSY_START_TIMEOUT, "Bewegung Start")
        self._wait_until_position_reached(
            target_mm=target_mm,
            timeout_s=self.MOVE_TIMEOUT,
            context="Bewegung nach Start",
            tol_mm=self.POSITION_TOL_MM,
        )

        print("[MixEngine] Position erreicht")

    def _dispense(self, pump_number: int, seconds: int):
        seconds = int(seconds)
        if self.is_simulation_mode():
            self._sim_log_mixer([3, int(pump_number), max(0, min(255, seconds))], note=f"CMD_PUMPE {pump_number} fuer {seconds}s")
            self.sim_trace.log_text(f"[SIM] Pumpe {pump_number} lief {seconds} s")
            return

        timeout = seconds + self.PUMP_TIMEOUT_EXTRA

        self._wait_until_idle(timeout, "Pumpen vor Start")

        print(f"[MixEngine] Starte Pumpe {pump_number} fuer {seconds} Sekunden")
        self.monitor.run_i2c(self.i2c.activate_pump, int(pump_number), seconds)

        self._wait_pump_started(self.BUSY_START_TIMEOUT, "Pumpen Start")
        self._wait_until_idle(timeout, "Pumpen nach Start")

        print(f"[MixEngine] Pumpe {pump_number} beendet")

    def _regal_wait_until_idle(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")
            if not bool(last.get("busy", False)):
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: Timeout, Regal blieb busy. Status={last}")

    def _regal_wait_for_position(self, target_mm: int, timeout_s: float, context: str):
        start = time.time()
        last = None
        target_mm = int(target_mm)
        while time.time() - start < timeout_s:
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")

            pos = last.get("ist_position")
            busy = bool(last.get("busy", False))
            try:
                pos_i = int(pos)
            except Exception:
                pos_i = None

            if pos_i is not None and (not busy) and abs(pos_i - target_mm) <= self.POSITION_TOL_MM:
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: Zielhoehe nicht erreicht. target_mm={target_mm}, Status={last}")

    def _regal_wait_for_homing_ok(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")
            if bool(last.get("homing_ok", False)) and (not bool(last.get("busy", False))):
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    def _regal_ensure_homed(self, safe_height_mm: int):
        if self.regal is None:
            raise RuntimeError("Regal-Homing nicht moeglich: Regal-Controller nicht verfuegbar.")

        st = self.regal.get_status()
        if not st.get("ok", False):
            raise RuntimeError(f"Regal-Homing: Status ungueltig. Status={st}")

        if bool(st.get("homing_ok", False)):
            print("[MixEngine] Regal: Lift bereits gehomed")
            return

        print("[MixEngine] Regal: Lift nicht gehomed, starte Homing")
        self._regal_wait_until_idle(self.REGAL_HOME_TIMEOUT, "Regal Homing vor Start")
        self.regal.home()
        self._regal_wait_for_homing_ok(self.REGAL_HOME_TIMEOUT, "Regal Homing")

        print(f"[MixEngine] Regal: Fahre auf sichere Homing-Hoehe ({safe_height_mm} mm)")
        self.regal.lift_to_mm(int(safe_height_mm))
        self._regal_wait_for_position(int(safe_height_mm), self.REGAL_MOVE_TIMEOUT, "Regal sichere Homing-Hoehe")

        print("[MixEngine] Regal: Home Ausschub am Initialgeber")
        self._regal_wait_until_idle(self.REGAL_AUSSCHUB_TIMEOUT, "Regal Ausschub-Homing vor Start")
        self.regal.home_ausschub()
        self._regal_wait_until_idle(self.REGAL_AUSSCHUB_TIMEOUT, "Regal Ausschub-Homing")

    def _regal_wait_for_glass_at_lift(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")
            if bool(last.get("band_belegt", False)):
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: Kein Glas am Lift erkannt (band_belegt blieb False). Status={last}")

    def _run_regal_sequence_if_available(self, mix_data: list):
        settings = SystemSettingsModel()
        if self.is_simulation_mode():
            if not mix_data:
                settings.close()
                return
            cocktail_id = mix_data[0].get("cocktail_id")
            level = settings.get_cocktail_source_level(int(cocktail_id)) if cocktail_id is not None else None
            if level is None:
                level = 1
            level_ausschub_mm = settings.get_level_ausschub_distance(int(level))
            if level_ausschub_mm is None:
                level_ausschub_mm = settings.get_ausschub_distance()
            if level_ausschub_mm is None:
                level_ausschub_mm = 0.0
            level_direction = settings.get_level_direction(int(level))
            if level_direction is None:
                level_direction = True
            load_unload_pos_mm = settings.get_load_unload_position()
            if load_unload_pos_mm is None:
                load_unload_pos_mm = settings.get_waiting_position()
            if load_unload_pos_mm is None:
                load_unload_pos_mm = 0.0
            homing_safe_height_mm = settings.get_homing_safe_height()
            if homing_safe_height_mm is None:
                homing_safe_height_mm = 0.0
            encoded_level = (int(level) & 0x3F) | 0x40 | (0x80 if bool(level_direction) else 0x00)
            direction_name = "vorwaerts" if level_direction else "rueckwaerts"
            self._sim_log_regal([1], note="CMD_HOME (Lift+Ausschub)")
            self._sim_log_regal([0, int(homing_safe_height_mm) & 0xFF, (int(homing_safe_height_mm) >> 8) & 0xFF], note=f"CMD_LIFT -> sichere Homing-Hoehe {int(homing_safe_height_mm)} mm")
            self._sim_log_mixer([0, int(load_unload_pos_mm) & 0xFF, (int(load_unload_pos_mm) >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {int(load_unload_pos_mm)} mm")
            self._sim_log_regal([6, int(level_ausschub_mm) & 0xFF, (int(level_ausschub_mm) >> 8) & 0xFF], note=f"CMD_AUSSCHUB -> {int(level_ausschub_mm)} mm")
            self._sim_log_regal(
                [3, int(encoded_level)],
                note=f"CMD_EBENE {level} ({direction_name}, ausschub={level_ausschub_mm})",
            )
            self._sim_log_regal([4], note="CMD_BELADEN")
            self._sim_log_mixer([0, int(load_unload_pos_mm) & 0xFF, (int(load_unload_pos_mm) >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {int(load_unload_pos_mm)} mm (vor Entladen)")
            self._sim_log_regal([6, int(level_ausschub_mm) & 0xFF, (int(level_ausschub_mm) >> 8) & 0xFF], note=f"CMD_AUSSCHUB -> {int(level_ausschub_mm)} mm (vor Entladen)")
            self._sim_log_regal([5], note="CMD_ENTLADEN")
            self.sim_trace.log_text("[SIM] Regal-Sequenz abgeschlossen")
            settings.close()
            return

        if not self.has_regal_controller():
            # Ohne Regal-Controller kann der Mix trotzdem laufen (nur ohne Regal-Automation).
            print("[MixEngine] Regal nicht erkannt, Regal-Sequenz wird uebersprungen")
            settings.close()
            return

        if not mix_data:
            settings.close()
            return

        cocktail_id = mix_data[0].get("cocktail_id")
        if cocktail_id is None:
            settings.close()
            raise RuntimeError("Regal-Sequenz: cocktail_id fehlt in den Mix-Daten.")

        level = settings.get_cocktail_source_level(int(cocktail_id))
        if level is None:
            settings.close()
            raise RuntimeError(f"Regal-Sequenz: Keine Quell-Ebene fuer Cocktail {cocktail_id} gesetzt.")

        level_direction = settings.get_level_direction(int(level))
        if level_direction is None:
            level_direction = True
        level_ausschub_mm = settings.get_level_ausschub_distance(int(level))
        if level_ausschub_mm is None:
            level_ausschub_mm = settings.get_ausschub_distance()
        if level_ausschub_mm is None:
            level_ausschub_mm = 0.0
        load_unload_pos_mm = settings.get_load_unload_position()
        if load_unload_pos_mm is None:
            load_unload_pos_mm = settings.get_waiting_position()
        if load_unload_pos_mm is None:
            settings.close()
            raise RuntimeError("Regal-Sequenz: load_unload_position_mm ist nicht gesetzt.")
        homing_safe_height_mm = settings.get_homing_safe_height()
        if homing_safe_height_mm is None:
            settings.close()
            raise RuntimeError("Regal-Sequenz: homing_safe_height_mm ist nicht gesetzt.")

        source_height_mm = settings.get_level_height(int(level))
        if source_height_mm is None:
            settings.close()
            raise RuntimeError(f"Regal-Sequenz: Hoehe fuer Ebene {level} nicht gesetzt.")

        mixer_height_mm = settings.get_mixer_height()
        if mixer_height_mm is None:
            settings.close()
            raise RuntimeError("Regal-Sequenz: mixer_height_mm ist nicht gesetzt.")

        settings.close()

        source_mm = int(round(float(source_height_mm)))
        mixer_mm = int(round(float(mixer_height_mm)))
        level_ausschub_i = int(round(float(level_ausschub_mm)))
        load_unload_i = int(round(float(load_unload_pos_mm)))
        homing_safe_i = int(round(float(homing_safe_height_mm)))

        self._regal_ensure_homed(homing_safe_i)

        # Reihenfolge ist bewusst strikt: Quelle -> Uebergabe -> Beladen -> Mixer -> Entladen.
        print(f"[MixEngine] Regal: Fahre Lift auf Ebene {level} (hoehe={source_mm} mm)")
        self._regal_wait_until_idle(self.REGAL_MOVE_TIMEOUT, "Regal vor Ebenenfahrt")
        self.regal.lift_to_mm(source_mm)
        self._regal_wait_for_position(source_mm, self.REGAL_MOVE_TIMEOUT, "Regal Ebenenfahrt")

        print(f"[MixEngine] Mixer: Fahre auf Uebergabeposition ({load_unload_i} mm)")
        self.move_to_position(load_unload_i)

        print(f"[MixEngine] Regal: Fahre Ausschub vor ({level_ausschub_i} mm) vor Beladen")
        self._regal_wait_until_idle(self.REGAL_AUSSCHUB_TIMEOUT, "Regal vor Ausschubfahrt (Beladen)")
        self.regal.ausschub_to_mm(level_ausschub_i)
        self._regal_wait_until_idle(self.REGAL_AUSSCHUB_TIMEOUT, "Regal Ausschubfahrt (Beladen)")

        direction_name = "vorwaerts" if level_direction else "rueckwaerts"
        print(
            f"[MixEngine] Regal: Waehle Ebene {level} (Richtung={direction_name}, Ausschub={level_ausschub_mm}) "
            "und starte Beladen bis Glas erkannt"
        )
        self.regal.select_level(int(level), forward=bool(level_direction))
        self.regal.beladen()
        self._regal_wait_for_glass_at_lift(self.REGAL_GLASS_WAIT_TIMEOUT, "Regal Beladen")

        print(f"[MixEngine] Regal: Fahre Lift auf Mixerhoehe ({mixer_mm} mm)")
        self.regal.lift_to_mm(mixer_mm)
        self._regal_wait_for_position(mixer_mm, self.REGAL_MOVE_TIMEOUT, "Regal Fahrt zum Mixer")

        print(f"[MixEngine] Mixer: Fahre auf Uebergabeposition ({load_unload_i} mm) vor Entladen")
        self.move_to_position(load_unload_i)

        print(f"[MixEngine] Regal: Fahre Ausschub vor ({level_ausschub_i} mm) vor Entladen")
        self._regal_wait_until_idle(self.REGAL_AUSSCHUB_TIMEOUT, "Regal vor Ausschubfahrt (Entladen)")
        self.regal.ausschub_to_mm(level_ausschub_i)
        self._regal_wait_until_idle(self.REGAL_AUSSCHUB_TIMEOUT, "Regal Ausschubfahrt (Entladen)")

        print("[MixEngine] Regal: Uebergabe an Mixer (Entladen)")
        st_before_unload = self.regal.get_status()
        if st_before_unload.get("entladen_blocked", False) or st_before_unload.get("wait_end_belegt", False):
            raise RuntimeError(
                "Regal Entladen blockiert: Wartepositions-Sensor 2 ist belegt. "
                "Entladen erst moeglich, wenn Sensor 2 frei ist."
            )
        self.regal.entladen()
        self._regal_wait_until_idle(self.REGAL_MOVE_TIMEOUT, "Regal Entladen")
        st_after_unload = self.regal.get_status()
        if st_after_unload.get("entladen_blocked", False):
            raise RuntimeError(
                "Regal Entladen blockiert waehrend Ablauf: Wartepositions-Sensor 2 belegt."
            )
        self._wait_for_mixer_glass_detected(
            timeout_s=self.MIXER_GLASS_WAIT_TIMEOUT,
            context="Regal Entladen",
        )

    def _wait_for_mixer_glass_detected(self, timeout_s: float, context: str):
        if self.is_simulation_mode():
            self.sim_trace.log_text("[SIM] Mixer-Sensor: Glas erkannt")
            return

        start = time.time()
        last_raw = b""

        while time.time() - start < timeout_s:
            last_raw = self.monitor.run_i2c(self.i2c.getstatus_raw)
            if len(last_raw) == 5 and bool(last_raw[1] & 0x01):
                return
            time.sleep(0.2)

        raise RuntimeError(
            f"{context}: Mixer-Sensor hat kein Glas erkannt (band_belegt blieb False). "
            f"raw={list(last_raw) if last_raw else []}"
        )

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten sind leer")

        order_list = [(x.get("order_index"), x.get("ingredient_name")) for x in mix_data]
        print("[MixEngine] Reihenfolge:", order_list)

        self.ensure_homed()
        # Vor dem Pumpen Regal-Sequenz fahren, falls Regal vorhanden.
        self._run_regal_sequence_if_available(mix_data)

        # Mixer-only Modus:
        # Wenn kein Regal erkannt wird, arbeiten wir ohne Lift/Ebenen
        # und pruefen nur, ob am Mixer ein Glas erkannt wird.
        if not self.has_regal_controller():
            print("[MixEngine] Regal nicht erkannt: Mixer-only Modus (ohne Lift/Ebenen)")
            self._wait_for_mixer_glass_detected(
                timeout_s=self.MIXER_GLASS_WAIT_TIMEOUT,
                context="Mixer-only Start",
            )

        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = float(item["amount_ml"]) * float(factor)
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_mm = item.get("position_mm", item.get("position_steps"))

            if pump_number is None or flow_rate is None or float(flow_rate) <= 0:
                print(f"[MixEngine] {ingredient}: ungueltige Pumpendaten, uebersprungen")
                continue

            print(f"[MixEngine] Fahre zu {ingredient} (Pumpe {pump_number})")
            self.move_to_position(position_mm)

            dispense_time_s = amount_ml / float(flow_rate)
            seconds = max(1, min(255, int(round(dispense_time_s))))

            self._dispense(pump_number, seconds)

        print("[MixEngine] Cocktail vollstaendig gemixt")
        return mix_data

    def close(self):
        try:
            self.monitor.stop()
        finally:
            try:
                self.i2c.close()
            finally:
                try:
                    if self.regal is not None:
                        self.regal.close()
                finally:
                    pass
