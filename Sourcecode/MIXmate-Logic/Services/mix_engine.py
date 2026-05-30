import threading
import time

from Hardware.i2C_logic import i2C_logic
from Hardware.regal_i2c_logic import RegalI2CLogic
from Model.system_settings_model import SystemSettingsModel
from Services.simulation_trace_service import get_simulation_trace_service
from Services.status_monitor import StatusMonitor
from Services.status_service import StatusService


class MixEngine:
    # Maximale Wartezeit fuer Mixer-Homing.
    HOME_TIMEOUT = 1800
    # Maximale Wartezeit fuer normale Mixerfahrten.
    MOVE_TIMEOUT = 1800
    # Zusatzpuffer fuer Pumpenlaufzeiten.
    PUMP_TIMEOUT_EXTRA = 1000
    # Prefix fuer Hinweise, die in der UI nicht als Crash wirken sollen.
    USER_INFO_PREFIX = "HINWEIS: "
    # Prefix fuer bewusst ausgeloeste Stop-Meldungen.
    STOP_INFO_PREFIX = "STOP: "

    # Zeitfenster, in dem eine Aktion Busy melden muss.
    BUSY_START_TIMEOUT = 1800
    # Kurzes Nachlauf-Fenster nach Homing fuer stabilen Status.
    POST_HOME_STATUS_SYNC_TIMEOUT = 180
    # Positionsvergleich ohne Toleranz, solange Firmware exakt meldet.
    POSITION_TOL_MM = 0
    # Regalbewegungen haben kuerzere mechanische Timeouts.
    REGAL_MOVE_TIMEOUT = 120.0
    REGAL_HOME_TIMEOUT = 180.0
    REGAL_GLASS_WAIT_TIMEOUT = 180.0
    REGAL_WAIT_TRANSFER_TIMEOUT = 120.0
    # Mixer-only Modus wartet nur begrenzt auf ein Glas.
    MIXER_GLASS_WAIT_TIMEOUT = 60.0
    # Ebene 3 ist im Regal-Protokoll die Warteposition.
    REGAL_WAIT_LEVEL_ID = 3

    def __init__(self):
        # Mixer-Arduino an Adresse 0x13.
        self.i2c = i2C_logic()
        # StatusService uebersetzt Rohbytes in Dicts.
        self.status_service = StatusService()
        # Hintergrund-Poller: hält den letzten Status bereit und serialisiert I2C-Zugriffe.
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()
        # Regal-Controller an Adresse 0x12 ist optional.
        self.regal = self._init_regal()
        # Trace zeigt simulierte I2C-Befehle im Adminmonitor.
        self.sim_trace = get_simulation_trace_service()
        # Simulationsposition ersetzt echte Encoderwerte.
        self._sim_position_mm = 0
        # Simulations-Homing ersetzt echtes homing_ok.
        self._sim_homed = False
        # Regal-Homing wird nur einmal pro Lauf erzwungen.
        self._regal_homed_once = False
        # Thread-sicheres Stop-Signal fuer lange Ablaufschritte.
        self._stop_requested = threading.Event()

    def _init_regal(self):
        # Regal-Controller am I2C-Bus suchen.
        try:
            regal = RegalI2CLogic()
            # Erster Statusread prueft, ob der zweite Controller antwortet.
            raw = regal.get_status_raw()
            if len(raw) == 5:
                print("[MixEngine] Regal-Controller erkannt (I2C 0x12)")
                return regal
            regal.close()
        except Exception as e:
            print(f"[MixEngine] Regal-Controller nicht erkannt: {e}")
        return None

    def has_regal_controller(self) -> bool:
        # Verfuegbarkeit der Regalsteuerung pruefen.
        if self.is_simulation_mode():
            return True
        if self.regal is None:
            return False
        st = self.regal.get_status()
        return bool(st.get("ok", False))

    def get_regal_status(self) -> dict:
        # Regalstatus lesen oder Simulationswerte liefern.
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
        # Mixerstatus und Regalstatus fuer die UI zusammenfuehren.
        if self.is_simulation_mode():
            status = self._sim_status()
        else:
            status = dict(self.monitor.get_latest() or {})
        regal_status = self.get_regal_status()
        # Regalwerte bekommen eigene Keys, damit Mixerwerte unveraendert bleiben.
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
        # Einstellung wird bewusst frisch aus der DB gelesen.
        settings = SystemSettingsModel()
        try:
            return bool(settings.get_simulation_mode())
        except Exception:
            # Bei Settings-Fehlern bleibt Hardwarebetrieb der sichere Default.
            return False
        finally:
            settings.close()

    def _sim_status(self) -> dict:
        # Minimaler Status fuer Betrieb ohne I2C-Hardware.
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
        # Simulierter Mixer-Befehl im Monitor sichtbar machen.
        self.sim_trace.log_i2c(0x13, payload, note=note)

    def _sim_log_regal(self, payload: list[int], note: str = ""):
        # Simulierter Regal-Befehl im Monitor sichtbar machen.
        self.sim_trace.log_i2c(0x12, payload, note=note)

    def _busy(self, status: dict) -> bool:
        # Helper kapselt fehlende Statuswerte als False.
        return bool((status or {}).get("busy", False))

    def _homing_ok(self, status: dict) -> bool:
        # Homing-Flag defensiv aus dem Status lesen.
        return bool((status or {}).get("homing_ok", False))

    def _position_mm(self, status: dict):
        # None bleibt erhalten, falls kein Positionswert vorliegt.
        return (status or {}).get("ist_position", None)

    def _refresh_status(self) -> dict:
        if self.is_simulation_mode():
            return self._sim_status()
        # Exklusiv lesen, damit Polling und aktive Kommandos sich nicht kollidieren
        raw = self.monitor.run_i2c(self.i2c.getstatus_raw)
        return self.status_service.parse_status(raw)

    def _raise_user_info(self, message: str):
        # Prefix trennt Bedienhinweise von echten Fehlern.
        raise RuntimeError(f"{self.USER_INFO_PREFIX}{message}")

    def _raise_stop_info(self, message: str = "Mixvorgang wurde gestoppt."):
        # Stop-Meldung wird in der UI gesondert behandelt.
        raise RuntimeError(f"{self.STOP_INFO_PREFIX}{message}")

    def _reset_stop_request(self):
        # Neuer Mix startet ohne alten Stop-Zustand.
        self._stop_requested.clear()

    def _check_stop_requested(self):
        # Stop-Flag wird in laengeren Warteschleifen regelmaessig geprueft.
        if not self._stop_requested.is_set():
            return
        self._abort_hardware_now()
        self._raise_stop_info()

    def _abort_hardware_now(self):
        # Laufende Mixer- und Regalbewegungen stoppen.
        if self.is_simulation_mode():
            self.sim_trace.log_text("[SIM] STOP angefordert")
            return

        try:
            self.monitor.run_i2c(self.i2c.stop, refresh_after=False)
        except Exception as e:
            print(f"[MixEngine] Stop Mixer fehlgeschlagen: {e}")

        try:
            if self.regal is not None:
                self.regal.stop()
        except Exception as e:
            print(f"[MixEngine] Stop Regal fehlgeschlagen: {e}")

    def request_stop(self):
        # Sofortigen Stop anfordern.
        self._stop_requested.set()
        self._abort_hardware_now()

    def _get_regal_homing_safe_height(self) -> int:
        # Sichere Lift-Hoehe fuer Homing aus den Maschinenparametern.
        settings = SystemSettingsModel()
        try:
            safe_height_mm = settings.get_homing_safe_height()
        finally:
            settings.close()
        if safe_height_mm is None:
            # Null bleibt Fallback, wenn kein Parameter gesetzt ist.
            return 0
        return int(round(float(safe_height_mm)))

    def _wait_until_idle(self, timeout_s: float, context: str):
        # Auf freien Mixer warten.
        # Zentraler Safety-Wait: viele Schritte dürfen nur im Idle starten.
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last = self._refresh_status()
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Ungueltiger Status (ok=False). Status={last}")
            if last.get("busy") is False:
                return
            time.sleep(0.2)

        raise RuntimeError(f"{context}: Timeout. busy blieb True. Status={last}")

    def _wait_for_homing_ok(self, timeout_s: float, context: str):
        # Auf bestaetigtes Homing warten.
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last = self._refresh_status()
            if (not self._busy(last)) and self._homing_ok(last):
                return
            time.sleep(0.2)

        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    def _wait_until_position_reached(self, target_mm: int, timeout_s: float, context: str, tol_mm: int = 0):
        # Auf Zielposition und Stillstand warten.
        start = time.time()
        last = None
        target_mm = int(target_mm)
        tol_mm = int(tol_mm)

        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last = self._refresh_status()
            pos = self._position_mm(last)

            if pos is not None:
                try:
                    # Positionswerte koennen aus DB/UI als floatartige Werte kommen.
                    pos_i = int(pos)
                except Exception:
                    pos_i = None

                if pos_i is not None and abs(pos_i - target_mm) <= tol_mm and (not self._busy(last)):
                    # Ziel gilt erst bei Positionstreffer und Stillstand als erreicht.
                    return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: Zielposition nicht erreicht. target_mm={target_mm}, Status={last}")

    def _wait_move_started(self, old_pos_mm: int, timeout_s: float, context: str):
        # Bewegungsstart erkennen.
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            self._check_stop_requested()
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

    def _wait_until_busy(self, timeout_s: float, context: str):
        # Auf Busy-Signal einer Aktion warten.
        start = time.time()
        last = None

        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last = self._refresh_status()
            if self._busy(last):
                return
            time.sleep(0.05)

        raise RuntimeError(f"{context}: Aktion hat nicht gestartet. Status={last}")

    def ensure_homed(self):
        # Mixer-Schlitten bei Bedarf referenzieren.
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
        # Mixer-Schlitten auf Zielposition fahren.
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

    LIFT_MIXER_SAFETY_MARGIN_MM = 70
    TRANSFER_APPROACH_MARGIN_MM = 100

    def _ensure_mixer_clear_for_lift(self, load_unload_i: int):
        # Mindestabstand zwischen Mixer und Lift-Uebergabe sicherstellen.
        if self.is_simulation_mode():
            cur = self._sim_position_mm
        else:
            st = self._refresh_status()
            cur = self._position_mm(st)
            if cur is None:
                return  # Position unbekannt, kein Sicherheits-Move moeglich
            cur = int(round(float(cur)))

        dist = abs(cur - load_unload_i)
        if dist < self.LIFT_MIXER_SAFETY_MARGIN_MM:
            if cur <= load_unload_i:
                safe_pos = load_unload_i - self.LIFT_MIXER_SAFETY_MARGIN_MM
            else:
                safe_pos = load_unload_i + self.LIFT_MIXER_SAFETY_MARGIN_MM
            print(
                f"[MixEngine] Sicherheits-Move: Mixer bei {cur} mm ist {dist} mm nah an"
                f" Uebergabe ({load_unload_i} mm). Fahre auf {safe_pos} mm."
            )
            self.move_to_position(safe_pos)

    def _move_mixer_away_from_transfer_position(self, load_unload_i: int, margin_mm: int = None):
        # Mixer vor dem Transfer aus dem Uebergabebereich fahren.
        if margin_mm is None:
            margin_mm = self.TRANSFER_APPROACH_MARGIN_MM

        if self.is_simulation_mode():
            cur = self._sim_position_mm
        else:
            st = self._refresh_status()
            cur = self._position_mm(st)
            if cur is None:
                return
            cur = int(round(float(cur)))

        dist = abs(cur - load_unload_i)
        if dist >= margin_mm:
            return

        if cur <= load_unload_i:
            safe_pos = load_unload_i - margin_mm
        else:
            safe_pos = load_unload_i + margin_mm

        print(
            f"[MixEngine] Mixer bleibt weg von der Uebergabe: "
            f"aktuell {cur} mm, Zielabstand mindestens {margin_mm} mm. "
            f"Fahre auf {safe_pos} mm."
        )
        self.move_to_position(safe_pos)

    def admin_move_mixer_to_position(self, target_mm: int):
        # Manuelle Mixerfahrt aus dem Adminbereich.
        self._reset_stop_request()
        self.ensure_homed()
        self.move_to_position(int(target_mm))

    def admin_move_regal_lift_to_position(self, target_mm: int):
        # Manuelle Regal-Liftfahrt aus dem Adminbereich.
        self._reset_stop_request()
        if self.is_simulation_mode():
            target_mm = int(target_mm)
            low = target_mm & 0xFF
            high = (target_mm >> 8) & 0xFF
            self._sim_log_regal([0, low, high], note=f"CMD_LIFT -> {target_mm} mm (Kalibrierung)")
            self._sim_position_mm = target_mm
            self.sim_trace.log_text(f"[SIM] Regal-Lift Kalibrierfahrt auf {target_mm} mm")
            return

        if self.regal is None:
            raise RuntimeError("Regal-Kalibrierung nicht moeglich: Regal-Controller nicht verfuegbar.")

        self._regal_ensure_homed_for_calibration(self._get_regal_homing_safe_height())
        self._regal_wait_until_idle(self.REGAL_MOVE_TIMEOUT, "Regal-Kalibrierung vor Liftfahrt")
        self.regal.lift_to_mm(int(target_mm))
        self._regal_wait_for_position(int(target_mm), self.REGAL_MOVE_TIMEOUT, "Regal-Kalibrierung Liftfahrt")

    def _dispense(self, pump_number: int, seconds: int):
        # Pumpe fuer die berechnete Zeit laufen lassen.
        seconds = int(seconds)
        if self.is_simulation_mode():
            self._sim_log_mixer([3, int(pump_number), max(0, min(255, seconds))], note=f"CMD_PUMPE {pump_number} fuer {seconds}s")
            self.sim_trace.log_text(f"[SIM] Pumpe {pump_number} lief {seconds} s")
            return

        timeout = seconds + self.PUMP_TIMEOUT_EXTRA

        self._wait_until_idle(timeout, "Pumpen vor Start")

        print(f"[MixEngine] Starte Pumpe {pump_number} fuer {seconds} Sekunden")
        self.monitor.run_i2c(self.i2c.activate_pump, int(pump_number), seconds)

        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Pumpen Start")
        self._wait_until_idle(timeout, "Pumpen nach Start")

        print(f"[MixEngine] Pumpe {pump_number} beendet")

    def _regal_wait_until_idle(self, timeout_s: float, context: str):
        # Auf freien Regal-Controller warten.
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")
            if not bool(last.get("busy", False)):
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: Timeout, Regal blieb busy. Status={last}")

    def _regal_wait_for_position(self, target_mm: int, timeout_s: float, context: str):
        # Auf Zielhoehe des Regal-Lifts warten.
        start = time.time()
        last = None
        target_mm = int(target_mm)
        while time.time() - start < timeout_s:
            self._check_stop_requested()
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
            self._check_stop_requested()
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")
            if bool(last.get("homing_ok", False)) and (not bool(last.get("busy", False))):
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    def _mixer_side_to_forward(self, mixer_direction_left: bool) -> bool:
        # Die DB speichert die Mixer-Seite als links/rechts.
        # Fuer das Liftband entspricht die physische Fahrtrichtung aktuell
        # der invertierten booleschen Richtung.
        return not bool(mixer_direction_left)

    def _waiting_side_to_forward(self, waiting_direction_left: bool) -> bool:
        # Die Warteposition ist mechanisch auf der Gegenseite verdrahtet.
        # Deshalb muss die gespeicherte links/rechts-Information fuer die
        # reale Lift-/Warteband-Richtung invertiert werden.
        return not bool(waiting_direction_left)

    def _regal_ensure_homed(self, safe_height_mm: int, load_unload_i: int = None):
        if self.regal is None:
            raise RuntimeError("Regal-Homing nicht moeglich: Regal-Controller nicht verfuegbar.")

        st = self.regal.get_status()
        if not st.get("ok", False):
            raise RuntimeError(f"Regal-Homing: Status ungueltig. Status={st}")

        if bool(st.get("homing_ok", False)):
            self._regal_homed_once = True
            print("[MixEngine] Regal: Lift bereits gehomed")
            return

        print("[MixEngine] Regal: Lift nicht gehomed, starte Homing")
        if load_unload_i is not None:
            self._ensure_mixer_clear_for_lift(load_unload_i)
        self._regal_wait_until_idle(self.REGAL_HOME_TIMEOUT, "Regal Homing vor Start")
        self.regal.home()
        self._regal_wait_for_homing_ok(self.REGAL_HOME_TIMEOUT, "Regal Homing")

        print(f"[MixEngine] Regal: Fahre auf sichere Homing-Hoehe ({safe_height_mm} mm)")
        self.regal.lift_to_mm(int(safe_height_mm))
        self._regal_wait_for_position(int(safe_height_mm), self.REGAL_MOVE_TIMEOUT, "Regal sichere Homing-Hoehe")

        self._regal_homed_once = True

    def _regal_ensure_homed_for_calibration(self, safe_height_mm: int):
        if self.regal is None:
            raise RuntimeError("Regal-Kalibrierung nicht moeglich: Regal-Controller nicht verfuegbar.")

        st = self.regal.get_status()
        if not st.get("ok", False):
            raise RuntimeError(f"Regal-Kalibrierung: Status ungueltig. Status={st}")

        if bool(st.get("homing_ok", False)):
            self._regal_homed_once = True
            return

        if self._regal_homed_once:
            print("[MixEngine] Regal-Kalibrierung: Homing wird uebersprungen (bereits in dieser Sitzung erfolgreich).")
            return

        self._regal_ensure_homed(safe_height_mm)

    def _regal_wait_for_glass_at_lift(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")
            if bool(last.get("band_belegt", False)):
                return last
            time.sleep(0.2)
        raise RuntimeError(f"{context}: Kein Glas am Lift erkannt (band_belegt blieb False). Status={last}")

    def _regal_wait_for_wait_position_transfer(self, timeout_s: float, context: str):
        # Glasuebergabe in die Warteposition ueberwachen.
        start = time.time()
        last = None
        state = "waiting_busy"

        while time.time() - start < timeout_s:
            last = self.regal.get_status() if self.regal else {"ok": False}
            if not last.get("ok", False):
                raise RuntimeError(f"{context}: Regal-Status ungueltig. Status={last}")

            busy = bool(last.get("busy", False))
            wait_start = bool(last.get("wait_start_belegt", False))
            wait_end = bool(last.get("wait_end_belegt", False))
            blocked = bool(last.get("entladen_blocked", False))

            if blocked:
                self._raise_user_info("Warteposition ist voll. Bitte Glaeser im Wartebereich entfernen.")

            # STATE 1: Warte bis Bewegung startet (busy=TRUE)
            if state == "waiting_busy":
                if busy:
                    state = "waiting_start_true"
                    print(f"[MixEngine] {context}: Bewegung gestartet (busy=1)")

            # STATE 2: Warte bis wait_start_belegt=TRUE (Glas tritt in Warteschiene ein)
            if state == "waiting_start_true":
                if wait_start:
                    state = "waiting_start_false"
                    print(f"[MixEngine] {context}: Glas tritt in Warteschiene ein (wait_start=1)")

            # STATE 3: Warte bis wait_start_belegt=FALSE (Glas hat Sensor passiert, liegt auf Schiene)
            if state == "waiting_start_false":
                if not wait_start:
                    print(f"[MixEngine] {context}: Glas vollstaendig auf Warteschiene (wait_start=0) - stoppe Foerderband")
                    self.regal.stop()
                    self._regal_wait_until_idle(self.REGAL_MOVE_TIMEOUT, f"{context} Stop")
                    return last

            time.sleep(0.2)

        raise RuntimeError(f"{context}: Timeout bei Warteposition-Uebergabe. State={state}")

    def _run_regal_sequence_if_available(self, mix_data: list):
        # Glas aus dem Regal holen und an den Mixer uebergeben.
        settings = SystemSettingsModel()
        if self.is_simulation_mode():
            if not mix_data:
                settings.close()
                return
            cocktail_id = mix_data[0].get("cocktail_id")
            level = settings.get_cocktail_source_level(int(cocktail_id)) if cocktail_id is not None else None
            if level is None:
                level = 1
            level_direction = settings.get_level_direction(int(level))
            if level_direction is None:
                level_direction = True
            mixer_direction = settings.get_mixer_direction()
            if mixer_direction is None:
                mixer_direction = True
            load_unload_pos_mm = settings.get_load_unload_position()
            if load_unload_pos_mm is None:
                load_unload_pos_mm = 0.0
            homing_safe_height_mm = settings.get_homing_safe_height()
            if homing_safe_height_mm is None:
                homing_safe_height_mm = 0.0
            encoded_level = (int(level) & 0x3F) | 0x40 | (0x80 if bool(level_direction) else 0x00)
            direction_name = "vorwaerts" if level_direction else "rueckwaerts"
            self._sim_log_regal([1], note="CMD_HOME (Lift)")
            self._sim_log_regal([0, int(homing_safe_height_mm) & 0xFF, (int(homing_safe_height_mm) >> 8) & 0xFF], note=f"CMD_LIFT -> sichere Homing-Hoehe {int(homing_safe_height_mm)} mm")
            load_unload_i = int(round(float(load_unload_pos_mm)))
            safe_pos = load_unload_i - self.TRANSFER_APPROACH_MARGIN_MM
            self._sim_log_mixer(
                [0, safe_pos & 0xFF, (safe_pos >> 8) & 0xFF],
                note=f"CMD_FAHR Mixer -> Abstand zur Uebergabe {safe_pos} mm",
            )
            self._sim_position_mm = safe_pos
            self._sim_log_regal(
                [3, int(encoded_level)],
                note=f"CMD_EBENE {level} (Ebene -> Lift, Richtung={direction_name})",
            )
            self._sim_log_regal([4], note="CMD_BELADEN")
            mixer_forward = self._mixer_side_to_forward(bool(mixer_direction))
            encoded_mixer_side = (int(level) & 0x3F) | 0x40 | (0x80 if mixer_forward else 0x00)
            mixer_direction_name = "links" if bool(mixer_direction) else "rechts"
            self._sim_log_regal(
                [3, int(encoded_mixer_side)],
                note=f"CMD_EBENE {level} (Lift -> Mixer, Richtung={mixer_direction_name})",
            )
            self._sim_log_mixer([0, int(load_unload_pos_mm) & 0xFF, (int(load_unload_pos_mm) >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {int(load_unload_pos_mm)} mm (vor Entladen)")
            self._sim_log_mixer([4], note="CMD_BELADEN Mixerband")
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
        mixer_direction = settings.get_mixer_direction()
        if mixer_direction is None:
            mixer_direction = True
        load_unload_pos_mm = settings.get_load_unload_position()
        if load_unload_pos_mm is None:
            settings.close()
            raise RuntimeError("Regal-Sequenz: load_unload_position_mm ist nicht gesetzt.")
        load_unload_height_mm = settings.get_load_unload_height()
        if load_unload_height_mm is None:
            load_unload_height_mm = settings.get_mixer_height()
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
        load_unload_i = int(round(float(load_unload_pos_mm)))
        load_unload_height_i = int(round(float(load_unload_height_mm)))
        homing_safe_i = int(round(float(homing_safe_height_mm)))

        self._regal_ensure_homed(homing_safe_i, load_unload_i)

        print(f"[MixEngine] Regal: Fahre Lift auf Ebene {level} (hoehe={source_mm} mm)")
        self._move_mixer_away_from_transfer_position(load_unload_i, self.TRANSFER_APPROACH_MARGIN_MM)
        self._ensure_mixer_clear_for_lift(load_unload_i)
        self._regal_wait_until_idle(self.REGAL_MOVE_TIMEOUT, "Regal vor Ebenenfahrt")
        self.regal.lift_to_mm(source_mm)
        self._regal_wait_for_position(source_mm, self.REGAL_MOVE_TIMEOUT, "Regal Ebenenfahrt")

        print(
            f"[MixEngine] Mixer: bleibt vorerst mit mindestens {self.TRANSFER_APPROACH_MARGIN_MM} mm "
            f"Abstand zur Uebergabeposition ({load_unload_i} mm)"
        )
        self._move_mixer_away_from_transfer_position(load_unload_i, self.TRANSFER_APPROACH_MARGIN_MM)

        direction_name = "vorwaerts" if level_direction else "rueckwaerts"
        print(
            f"[MixEngine] Regal: Waehle Ebene {level} (Richtung={direction_name}) "
            "und starte Beladen bis Glas erkannt"
        )
        self.regal.select_level(int(level), forward=bool(level_direction))
        self.regal.beladen()
        self._regal_wait_for_glass_at_lift(self.REGAL_GLASS_WAIT_TIMEOUT, "Regal Beladen")

        print(f"[MixEngine] Regal: Fahre Lift auf Uebergabehoehe ({load_unload_height_i} mm)")
        self._ensure_mixer_clear_for_lift(load_unload_i)
        self.regal.lift_to_mm(load_unload_height_i)
        self._regal_wait_for_position(load_unload_height_i, self.REGAL_MOVE_TIMEOUT, "Regal Fahrt zur Uebergabehoehe")

        print(f"[MixEngine] Mixer: Fahre auf Uebergabeposition ({load_unload_i} mm) vor Entladen")
        self.move_to_position(load_unload_i)

        mixer_direction_name = "links" if bool(mixer_direction) else "rechts"
        mixer_forward = self._mixer_side_to_forward(bool(mixer_direction))
        print(f"[MixEngine] Regal: Master setzt Richtung fuer Lift -> Mixer auf {mixer_direction_name}")
        self.regal.select_level(int(level), forward=mixer_forward)

        print("[MixEngine] Mixer: Starte Beladen fuer Bandlauf zur Uebergabe")
        self.monitor.run_i2c(self.i2c.beladen)

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

    def _return_glass_to_wait_position_if_available(self):
        # Glas nach dem Mix in die Warteposition zurueckgeben.
        settings = SystemSettingsModel()
        if self.is_simulation_mode():
            load_unload_pos_mm = settings.get_load_unload_position()
            waiting_height_mm = settings.get_waiting_position()
            waiting_direction = settings.get_waiting_direction()
            settings.close()

            if load_unload_pos_mm is None:
                load_unload_pos_mm = 0.0
            if waiting_height_mm is None:
                waiting_height_mm = 0.0
            if waiting_direction is None:
                waiting_direction = True

            load_unload_i = int(round(float(load_unload_pos_mm)))
            waiting_height_i = int(round(float(waiting_height_mm)))
            waiting_forward = self._waiting_side_to_forward(bool(waiting_direction))
            encoded_wait_level = (
                (int(self.REGAL_WAIT_LEVEL_ID) & 0x3F)
                | 0x40
                | (0x80 if waiting_forward else 0x00)
            )

            self._sim_log_mixer(
                [0, load_unload_i & 0xFF, (load_unload_i >> 8) & 0xFF],
                note=f"CMD_FAHR Mixer -> Uebergabe {load_unload_i} mm (Rueckgabe)",
            )
            self._sim_log_regal([3, encoded_wait_level], note="CMD_EBENE Warteposition")
            self._sim_log_regal([4], note="CMD_BELADEN Lift <- Mixer")
            self._sim_log_mixer([5], note="CMD_ENTLADEN Mixerband -> Lift")
            self._sim_log_regal(
                [0, waiting_height_i & 0xFF, (waiting_height_i >> 8) & 0xFF],
                note=f"CMD_LIFT -> Warteposition {waiting_height_i} mm",
            )
            self._sim_log_regal([5], note="CMD_ENTLADEN Lift -> Warteposition")
            self.sim_trace.log_text("[SIM] Glas in Warteposition abgelegt")
            return

        if not self.has_regal_controller():
            return

        load_unload_pos_mm = settings.get_load_unload_position()
        if load_unload_pos_mm is None:
            settings.close()
            raise RuntimeError("Regal-Rueckgabe: load_unload_position_mm ist nicht gesetzt.")

        waiting_height_mm = settings.get_waiting_position()
        if waiting_height_mm is None:
            settings.close()
            raise RuntimeError("Regal-Rueckgabe: waiting_position_mm ist nicht gesetzt.")

        mixer_direction = settings.get_mixer_direction()
        waiting_direction = settings.get_waiting_direction()
        settings.close()
        if mixer_direction is None:
            mixer_direction = True
        if waiting_direction is None:
            waiting_direction = True

        load_unload_i = int(round(float(load_unload_pos_mm)))
        waiting_height_i = int(round(float(waiting_height_mm)))

        st = self.regal.get_status()
        if not st.get("ok", False):
            raise RuntimeError(f"Regal-Rueckgabe: Regal-Status ungueltig. Status={st}")
        if bool(st.get("wait_end_belegt", False)) or bool(st.get("wait_start_belegt", False)):
            self._raise_user_info("Warteposition ist voll. Bitte Glaeser im Wartebereich entfernen.")

        print(f"[MixEngine] Mixer: Fahre auf Uebergabeposition ({load_unload_i} mm) fuer Rueckgabe")
        self.move_to_position(load_unload_i)

        print("[MixEngine] Regal: Starte Rueckgabe vom Mixer auf den Lift")
        self._regal_wait_until_idle(self.REGAL_GLASS_WAIT_TIMEOUT, "Regal vor Rueckgabe auf Lift")
        mixer_to_lift_direction = not self._mixer_side_to_forward(bool(mixer_direction))
        print(
            f"[MixEngine] Regal: Master setzt Richtung fuer Mixer -> Lift auf "
            f"{'links' if mixer_to_lift_direction else 'rechts'}"
        )
        self.regal.select_level(int(self.REGAL_WAIT_LEVEL_ID), forward=mixer_to_lift_direction)
        self.regal.beladen()

        print("[MixEngine] Mixer: Starte Entladen zur Rueckgabe auf den Lift")
        self.monitor.run_i2c(self.i2c.entladen)
        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Mixer Rueckgabe Start")

        self._regal_wait_for_glass_at_lift(self.REGAL_GLASS_WAIT_TIMEOUT, "Rueckgabe Mixer -> Lift")
        self._regal_wait_until_idle(self.REGAL_GLASS_WAIT_TIMEOUT, "Rueckgabe Mixer -> Lift (Regal)")
        self._wait_until_idle(self.MOVE_TIMEOUT, "Rueckgabe Mixer -> Lift (Mixer)")

        print(f"[MixEngine] Regal: Fahre Lift auf Wartehoehe ({waiting_height_i} mm)")
        self._ensure_mixer_clear_for_lift(load_unload_i)
        self.regal.lift_to_mm(waiting_height_i)
        self._regal_wait_for_position(waiting_height_i, self.REGAL_MOVE_TIMEOUT, "Regal Fahrt zur Warteposition")

        st_before_wait = self.regal.get_status()
        if not st_before_wait.get("ok", False):
            raise RuntimeError(f"Regal-Rueckgabe: Regal-Status vor Wartepositionsfahrt ungueltig. Status={st_before_wait}")
        if bool(st_before_wait.get("wait_end_belegt", False)) or bool(st_before_wait.get("wait_start_belegt", False)):
            self._raise_user_info("Warteposition ist voll. Bitte Glaeser im Wartebereich entfernen.")

        print("[MixEngine] Regal: Uebergabe vom Lift an die Warteposition")
        self._regal_wait_until_idle(self.REGAL_WAIT_TRANSFER_TIMEOUT, "Regal vor Wartepositions-Uebergabe")
        waiting_forward = self._waiting_side_to_forward(bool(waiting_direction))
        print(
            f"[MixEngine] Regal: Master setzt Richtung fuer Lift -> Warteposition auf "
            f"{'links' if bool(waiting_direction) else 'rechts'}"
        )
        self.regal.select_level(int(self.REGAL_WAIT_LEVEL_ID), forward=waiting_forward)
        self.regal.entladen()
        self._regal_wait_for_wait_position_transfer(
            self.REGAL_WAIT_TRANSFER_TIMEOUT,
            "Regal Wartepositions-Uebergabe",
        )

    def _wait_for_mixer_glass_detected(self, timeout_s: float, context: str):
        # Auf Glas am Mixer-Sensor warten.
        if self.is_simulation_mode():
            self.sim_trace.log_text("[SIM] Mixer-Sensor: Glas erkannt")
            return

        start = time.time()
        last_raw = b""

        while time.time() - start < timeout_s:
            self._check_stop_requested()
            last_raw = self.monitor.run_i2c(self.i2c.getstatus_raw)
            if len(last_raw) == 5 and bool(last_raw[1] & 0x01):
                return
            time.sleep(0.2)

        raise RuntimeError(
            f"{context}: Mixer-Sensor hat kein Glas erkannt (band_belegt blieb False). "
            f"raw={list(last_raw) if last_raw else []}"
        )

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        # Vollstaendigen Mixablauf fuer ein Rezept ausfuehren.
        if not mix_data:
            raise ValueError("Mix-Daten sind leer")

        self._reset_stop_request()

        order_list = [(x.get("order_index"), x.get("ingredient_name")) for x in mix_data]
        print("[MixEngine] Reihenfolge:", order_list)

        self.ensure_homed()
        # Vor dem Pumpen Regal-Sequenz fahren, falls Regal vorhanden.
        self._run_regal_sequence_if_available(mix_data)

        # Mixer-only Modus ohne Lift und Ebenen.
        # Glas-Sensor am Mixer bleibt der Startschutz.
        if not self.has_regal_controller():
            print("[MixEngine] Regal nicht erkannt: Mixer-only Modus (ohne Lift/Ebenen)")
            self._wait_for_mixer_glass_detected(
                timeout_s=self.MIXER_GLASS_WAIT_TIMEOUT,
                context="Mixer-only Start",
            )

        for item in mix_data:
            self._check_stop_requested()
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

        self._check_stop_requested()
        self._return_glass_to_wait_position_if_available()

        print("[MixEngine] Cocktail vollstaendig gemixt")
        return mix_data

    def close(self):
        # Polling stoppen und Hardwareverbindungen schliessen.
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
