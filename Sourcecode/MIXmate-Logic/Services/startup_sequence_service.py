# Relaisboard fuer die Startsequenz.
from Hardware.relay_board import RelayBoard
import time

class StartupSequenceService:
    def __init__(self, relay_board: RelayBoard):
        self.relay_board = relay_board

    def run(self, first_pair: list[int], second_pair: list[int], delay_secs: float):
        # Relaispaare nacheinander einschalten.
        print("Starte Initialisierungssequenz für Relais...")

        print("Einschalten des ersten Relais-Paares...")
        self.relay_board.set_many(first_pair, True)
        time.sleep(delay_secs)

        print("Einschalten des zweiten Relais-Paares...")
        self.relay_board.set_many(second_pair, True)
        time.sleep(delay_secs)

        print("Initialisierungssequenz abgeschlossen.")
