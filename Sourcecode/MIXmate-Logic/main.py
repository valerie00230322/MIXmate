import os
from Controller.admin_controller import AdminController
from Controller.mix_controller import MixController
from Controller.pump_controller import PumpController
from Model.mix_model import MixModel
from Model.pump_model import PumpModel
from Model.system_settings_model import SystemSettingsModel
from Services.simulation_trace_service import get_simulation_trace_service
from View.qt.run_qt import run_qt


class NoHardwareMixController:
    def __init__(self, db_path: str, init_error: Exception | None = None):
        # Mix-Controller fuer Betrieb ohne I2C-Hardware.
        # Startfehler der echten Hardware bleibt fuer Statusmeldungen erhalten.
        self._init_error = init_error
        # Gemeinsamer DB-Pfad fuer Models und Settings.
        self.db_path = db_path
        # MixModel liefert Rezepte auch im Laptop-Modus.
        self.model = MixModel(db_path=db_path)
        # Simulationsmonitor ersetzt sichtbare I2C-Aktivitaet.
        self.sim_trace = get_simulation_trace_service()
        # Simulierter Positionswert fuer Statusanzeigen.
        self._sim_position_mm = 0
        # Simuliertes Homing-Flag fuer Startfreigaben.
        self._sim_homed = False
        # Einfaches Stop-Flag reicht im Fallback ohne Worker-Synchronisierung.
        self._stop_requested = False

    def _simulation_enabled(self) -> bool:
        # Simulationsstatus aus den Systemeinstellungen.
        settings = SystemSettingsModel(db_path=self.db_path)
        try:
            return bool(settings.get_simulation_mode())
        finally:
            settings.close()

    def _assert_simulation_enabled(self):
        # Schutz gegen versehentliche Hardwareaktionen im Laptop-Modus.
        if not self._simulation_enabled():
            raise RuntimeError("Hardware nicht verfuegbar (I2C). Bitte Simulation im Admin aktivieren.")

    def _sim_log_mixer(self, payload: list[int], note: str = ""):
        # Mixer-I2C-Befehl nur in den Simulationsmonitor schreiben.
        self.sim_trace.log_i2c(0x13, payload, note=note)

    def _sim_log_regal(self, payload: list[int], note: str = ""):
        # Regal-I2C-Befehl nur in den Simulationsmonitor schreiben.
        self.sim_trace.log_i2c(0x12, payload, note=note)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        # Rezept laden und simulierten Mix starten.
        mix_data = self.prepare_mix(cocktail_id)
        return self.run_mix(mix_data, factor=factor)

    def get_status(self):
        # Maschinenstatus fuer den Laptop-Modus.
        if self._simulation_enabled():
            # Vollstaendiger Fake-Status haelt die UI im Laptop-Modus bedienbar.
            return {
                "ok": True,
                "severity": "OK",
                "error_code": None,
                "error_msg": "SIMULATION_MODE (ohne Hardware)",
                "busy": False,
                "band_belegt": True,
                "ist_position": int(self._sim_position_mm),
                "homing_ok": bool(self._sim_homed),
                "regal_connected": True,
                "regal_ok": True,
                "regal_busy": False,
                "regal_band_belegt": True,
                "regal_lift_sensor_belegt": True,
                "regal_wait_start_belegt": False,
                "regal_wait_end_belegt": False,
                "regal_level1_front_belegt": True,
                "regal_level2_front_belegt": True,
                "regal_mixer_belegt": True,
                "regal_entladen_blocked": False,
                "regal_ist_position": int(self._sim_position_mm),
                "regal_homing_ok": bool(self._sim_homed),
                "regal_error_msg": "SIMULATION_MODE",
            }

        msg = "Hardware nicht verfuegbar (I2C)."
        if self._init_error is not None:
            # Ursprungsfehler bleibt fuer Diagnose sichtbar.
            msg = f"{msg} Detail: {self._init_error}"
        return {
            "ok": False,
            "severity": "error",
            "error_code": "I2C_UNAVAILABLE",
            "error_msg": msg,
            "busy": False,
            "band_belegt": False,
            "ist_position": None,
            "homing_ok": False,
            "regal_connected": False,
            "regal_ok": False,
            "regal_busy": False,
            "regal_band_belegt": False,
            "regal_lift_sensor_belegt": False,
            "regal_wait_start_belegt": False,
            "regal_wait_end_belegt": False,
            "regal_level1_front_belegt": False,
            "regal_level2_front_belegt": False,
            "regal_mixer_belegt": False,
            "regal_entladen_blocked": False,
            "regal_ist_position": None,
            "regal_homing_ok": False,
            "regal_error_msg": "Regal nicht verfuegbar (Laptop-Modus).",
        }

    def prepare_mix(self, cocktail_id: int):
        # Rezeptdaten mit Cocktail-ID pro Schritt vorbereiten.
        self._assert_simulation_enabled()
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            # Leerer DB-Treffer bedeutet: Cocktail hat kein startbares Rezept.
            raise ValueError(f"Kein Rezept fuer Cocktail-ID {cocktail_id} gefunden.")
        for item in mix_data:
            # Cocktail-ID wird in jedem Schritt fuer Level-Zuordnung gebraucht.
            item["cocktail_id"] = int(cocktail_id)
        return mix_data

    def run_mix(self, mix_data, factor: float = 1.0):
        # Simulierter Regal-, Mixer- und Pumpenablauf.
        self._assert_simulation_enabled()
        if not mix_data:
            # Ohne Schritte gibt es keinen Ablauf fuer den Monitor.
            raise ValueError("Mix-Daten sind leer")
        # Alter Stop-Zustand darf keinen neuen Mix abbrechen.
        self._stop_requested = False

        cocktail_id = mix_data[0].get("cocktail_id")
        settings = SystemSettingsModel(db_path=self.db_path)
        try:
            # Maschinenparameter kommen aus der gleichen DB wie das Rezept.
            level = settings.get_cocktail_source_level(int(cocktail_id)) if cocktail_id is not None else None
            load_unload_pos_mm = settings.get_load_unload_position()
            if load_unload_pos_mm is None:
                # Nullpunkt ist der sichere Simulations-Fallback.
                load_unload_pos_mm = 0.0
            waiting_height_mm = settings.get_waiting_position()
            if waiting_height_mm is None:
                waiting_height_mm = 0.0
            homing_safe_height_mm = settings.get_homing_safe_height()
            if homing_safe_height_mm is None:
                homing_safe_height_mm = 0.0
            level_direction = settings.get_level_direction(int(level)) if level is not None else None
        finally:
            settings.close()
        if level is None:
            # Ebene 1 bleibt Standard, wenn kein Cocktail-Level gesetzt ist.
            level = 1
        if level_direction is None:
            # Vorwaerts ist Default fuer nicht konfigurierte Ebenen.
            level_direction = True

        # Firmware-Payload braucht ganze Millimeter.
        load_unload_i = int(round(float(load_unload_pos_mm)))
        waiting_height_i = int(round(float(waiting_height_mm)))
        homing_safe_i = int(round(float(homing_safe_height_mm)))
        # Level und Richtung werden wie in der Regal-Firmware codiert.
        encoded_level = (int(level) & 0x3F) | 0x40 | (0x80 if bool(level_direction) else 0x00)
        encoded_wait_level = (3 & 0x3F) | 0x40 | 0x80
        direction_name = "vorwaerts" if level_direction else "rueckwaerts"
        # Regal-/Mixer-Sequenz wird nur geloggt, damit die Schritte im Monitor nachvollziehbar bleiben.
        self._sim_log_mixer([1], note="CMD_HOME")
        self._sim_homed = True
        self._sim_position_mm = 0
        self._sim_log_regal([1], note="CMD_HOME (Lift)")
        self._sim_log_regal([0, homing_safe_i & 0xFF, (homing_safe_i >> 8) & 0xFF], note=f"CMD_LIFT -> sichere Homing-Hoehe {homing_safe_i} mm")
        self._sim_log_mixer([0, load_unload_i & 0xFF, (load_unload_i >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {load_unload_i} mm")
        self._sim_position_mm = load_unload_i
        self._sim_log_regal(
            [3, int(encoded_level)],
            note=f"CMD_EBENE {level} ({direction_name})",
        )
        self._sim_log_regal([4], note="CMD_BELADEN")
        self._sim_log_mixer([0, load_unload_i & 0xFF, (load_unload_i >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {load_unload_i} mm (vor Entladen)")
        self._sim_position_mm = load_unload_i
        self._sim_log_mixer([4], note="CMD_BELADEN Mixerband")
        self._sim_log_regal([5], note="CMD_ENTLADEN")
        self.sim_trace.log_text("[SIM] Regal-Sequenz abgeschlossen")

        for item in mix_data:
            if self._stop_requested:
                raise RuntimeError("STOP: Mixvorgang wurde gestoppt.")
            # Rezeptzeile in pumpbare Werte umwandeln.
            ingredient = str(item["ingredient_name"])
            amount_ml = float(item["amount_ml"]) * float(factor)
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_mm = int(item.get("position_mm", item.get("position_steps")))

            if pump_number is None or flow_rate is None or float(flow_rate) <= 0:
                # Ungueltige Pumpendaten werden in der Simulation nur protokolliert.
                self.sim_trace.log_text(f"[SIM] {ingredient}: ungueltige Pumpendaten, uebersprungen")
                continue

            # Positionswert in zwei Bytes fuer CMD_FAHR aufteilen.
            low = position_mm & 0xFF
            high = (position_mm >> 8) & 0xFF
            self._sim_log_mixer([0, low, high], note=f"CMD_FAHR -> {position_mm} mm")
            self._sim_position_mm = position_mm

            # Pumpenlaufzeit aus Menge und Kalibrierwert berechnen.
            dispense_time_s = amount_ml / float(flow_rate)
            # Firmware akzeptiert Sekunden als uint8.
            seconds = max(1, min(255, int(round(dispense_time_s))))
            self._sim_log_mixer([3, int(pump_number), seconds], note=f"CMD_PUMPE {pump_number} fuer {seconds}s")
            self.sim_trace.log_text(f"[SIM] Schritt: {ingredient}, {amount_ml:.1f} ml")

        if self._stop_requested:
            raise RuntimeError("STOP: Mixvorgang wurde gestoppt.")
        self._sim_log_mixer(
            [0, load_unload_i & 0xFF, (load_unload_i >> 8) & 0xFF],
            note=f"CMD_FAHR Mixer -> Uebergabe {load_unload_i} mm (Rueckgabe)",
        )
        self._sim_position_mm = load_unload_i
        self._sim_log_regal([3, encoded_wait_level], note="CMD_EBENE Warteposition")
        self._sim_log_regal([4], note="CMD_BELADEN Lift <- Mixer")
        self._sim_log_mixer([5], note="CMD_ENTLADEN Mixerband -> Lift")
        self._sim_log_regal(
            [0, waiting_height_i & 0xFF, (waiting_height_i >> 8) & 0xFF],
            note=f"CMD_LIFT -> Warteposition {waiting_height_i} mm",
        )
        self._sim_log_regal([5], note="CMD_ENTLADEN Lift -> Warteposition")
        self.sim_trace.log_text("[SIM] Glas in Warteposition abgelegt")
        self.sim_trace.log_text("[SIM] Cocktail vollstaendig gemixt")
        return mix_data

    def request_stop(self):
        # Stop-Wunsch fuer den laufenden simulierten Mix.
        self._stop_requested = True
        self.sim_trace.log_text("[SIM] STOP angefordert")

    def move_mixer_to_position(self, position_mm: int):
        # Simulierte Kalibrierfahrt des Mixers.
        mm = int(position_mm)
        # Position wird wie beim echten I2C-Befehl in Low/High zerlegt.
        self._sim_log_mixer([0, mm & 0xFF, (mm >> 8) & 0xFF], note=f"CMD_FAHR -> {mm} mm (Kalibrierung)")
        self._sim_position_mm = mm

    def move_regal_lift_to_position(self, position_mm: int):
        # Simulierte Kalibrierfahrt des Regal-Lifts.
        mm = int(position_mm)
        # Lift-Zielhoehe bleibt im Monitor nachvollziehbar.
        self._sim_log_regal([0, mm & 0xFF, (mm >> 8) & 0xFF], note=f"CMD_LIFT -> {mm} mm (Kalibrierung)")


    def shutdown(self):
        return None


class NoHardwarePumpController:
    def __init__(self, db_path=None):
        # Pumpen-Controller fuer Simulation und DB-Pflege.
        self.db_path = db_path
        self.model = PumpModel(db_path=db_path)
        self.sim_trace = get_simulation_trace_service()

    def _simulation_enabled(self) -> bool:
        # Pumpen-Fallback darf nur im aktivierten Simulationsmodus laufen.
        settings = SystemSettingsModel(db_path=self.db_path)
        try:
            return bool(settings.get_simulation_mode())
        finally:
            settings.close()

    def list_pumps(self):
        # Pumpenliste kommt weiter direkt aus der DB.
        return self.model.get_all_pumps()

    def set_position_steps(self, pump_number: int, steps: int):
        # Alter Methodenname leitet auf mm-Speicherung weiter.
        self.set_position_mm(pump_number, steps)

    def set_position_mm(self, pump_number: int, position_mm: int):
        # Kalibrierposition in der Pumpentabelle speichern.
        self.model.update_position_mm(pump_number, position_mm)

    def set_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        # Gemessene Flow-Rate persistieren.
        self.model.update_flow_rate(pump_number, flow_rate_ml_s)

    def assign_ingredient(self, pump_number: int, ingredient_id: int):
        # Zutat-Pumpe-Zuordnung in der DB aktualisieren.
        self.model.update_ingredient(pump_number, ingredient_id)

    def ensure_homed(self):
        # Homing-Eintrag fuer die Kalibrieransicht.
        if self._simulation_enabled():
            self.sim_trace.log_i2c(0x13, [1], note="CMD_HOME")
            return
        raise RuntimeError("Homing nicht moeglich: Hardware/I2C nicht verfuegbar.")

    def move_to_position(self, position_mm: int):
        if self._simulation_enabled():
            mm = int(position_mm)
            # Kalibrierfahrt ohne Hardware im Monitor anzeigen.
            self.sim_trace.log_i2c(0x13, [0, mm & 0xFF, (mm >> 8) & 0xFF], note=f"CMD_FAHR -> {mm} mm")
            return
        raise RuntimeError("Bewegung nicht moeglich: Hardware/I2C nicht verfuegbar.")

    def run_pump_for_calibration(self, pump_number: int, seconds: int):
        # Simulierter Pumpenlauf fuer die Kalibrierung.
        if self._simulation_enabled():
            # Sekunden auf Firmwarebereich begrenzen.
            sec = max(1, min(255, int(seconds)))
            self.sim_trace.log_i2c(0x13, [3, int(pump_number), sec], note=f"CMD_PUMPE (Kalibrierung) {pump_number} fuer {sec}s")
            self.sim_trace.log_text(f"[SIM] Kalibrierlauf beendet: Pumpe {pump_number}, {sec}s")
            return sec
        raise RuntimeError("Pumpenlauf nicht moeglich: Hardware/I2C nicht verfuegbar.")

    def save_flow_rate_from_measurement(self, pump_number: int, measured_ml: float, seconds: int):
        if seconds <= 0:
            # Division durch Null und negative Laufzeiten verhindern.
            raise ValueError("seconds muss > 0 sein")
        flow_rate = float(measured_ml) / float(seconds)
        if flow_rate <= 0:
            # Nur positive Messwerte ergeben eine brauchbare Kalibrierung.
            raise ValueError("Gemessener Flow muss > 0 sein")
        self.model.update_flow_rate(pump_number, flow_rate)
        return flow_rate


class MIXmate:
    def __init__(self):
        # Controller, Datenbank und Hardware-Fallback verdrahten.
        base = os.path.dirname(__file__)
        db_path = os.path.join(base, "Database", "MIXmate.db")
        init_error = None
        try:
            # Normalfall: echte Hardware-Controller starten.
            self.mix_controller = MixController(db_path=db_path)
            self.pump_controller = PumpController(self.mix_controller.engine, db_path=db_path)
        except Exception as e:
            init_error = e
            print(f"[Startup] Hardware nicht verfuegbar, starte im Laptop-Modus: {e}")
            # Fallback haelt UI und DB-Pflege auch ohne I2C lauffaehig.
            self.mix_controller = NoHardwareMixController(db_path=db_path, init_error=e)
            self.pump_controller = NoHardwarePumpController(db_path=db_path)
        self.admin_controller = AdminController(db_path=db_path)
        self.init_error = init_error

    def run(self):
        run_qt(self.mix_controller, self.pump_controller, self.admin_controller)


if __name__ == "__main__":
    app = MIXmate()
    app.run()
