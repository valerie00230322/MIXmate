from Services.mix_engine import MixEngine
from Model.mix_model import MixModel


class MixController:
    def __init__(self, db_path=None):
        # Engine steuert Hardware, Model liefert Rezeptdaten.
        self.engine = MixEngine()
        self.model = MixModel(db_path=db_path)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        # Rezept vor dem Start vollstaendig aus der DB laden.
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            # Ohne Rezeptdaten kann kein sinnvoller Ablauf gebaut werden.
            raise ValueError(f"Kein Rezept fuer Cocktail-ID {cocktail_id} gefunden.")
        for item in mix_data:
            # Cocktail-ID bleibt pro Schritt fuer Regal- und Level-Logik verfuegbar.
            item["cocktail_id"] = int(cocktail_id)
        return self.engine.mix_cocktail(mix_data, factor)

    def get_status(self):
        # Kombinierter Mixer- und Regalstatus fuer die UI.
        return self.engine.get_status()

    # Fuer GUI: vorbereiten des DB Teils im UI Thread, verhindert GUI freeze.
    def prepare_mix(self, cocktail_id: int):
        # DB-Zugriff vor dem Worker-Thread erledigen.
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept fuer Cocktail-ID {cocktail_id} gefunden.")
        for item in mix_data:
            item["cocktail_id"] = int(cocktail_id)
        return mix_data

    def run_mix(self, mix_data, factor: float = 1.0):
        # Vorbereitete Rezeptdaten an die Hardware-Engine geben.
        return self.engine.mix_cocktail(mix_data, factor)

    def request_stop(self):
        # Stop wird direkt an die Engine weitergereicht.
        self.engine.request_stop()

    def move_mixer_to_position(self, position_mm: int):
        # Adminfahrt nutzt dieselben Sicherheitschecks wie der Mixablauf.
        self.engine.admin_move_mixer_to_position(int(position_mm))

    def move_regal_lift_to_position(self, position_mm: int):
        # Manuelle Liftfahrt fuer Setup und Kalibrierung.
        self.engine.admin_move_regal_lift_to_position(int(position_mm))

    def shutdown(self):
        # Hardware-Polling zuerst stoppen, danach DB-Verbindung schliessen.
        try:
            self.engine.close()
        finally:
            self.model.close()
