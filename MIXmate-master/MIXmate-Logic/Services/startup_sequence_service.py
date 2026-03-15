# wird für relais benötigt
from Hardware.relay_board import RelayBoard
import time

class StartupSequenceService:
    def __init__(self, relay_board: RelayBoard):
        self.relay_board = relay_board

    def run(self, first_pair: list[int], second_pair: list[int], delay_secs: float):
        print("Starte Initialisierungssequenz für Relais...")

        print("Einschalten des ersten Relais-Paares...")
        self.relay_board.set_many(first_pair, True)
        time.sleep(delay_secs)

        """ print("Ausschalten des ersten Relais-Paares...")
        self.relay_board.set_many(first_pair, False)
        time.sleep(0.5) """

        print("Einschalten des zweiten Relais-Paares...")
        self.relay_board.set_many(second_pair, True)
        time.sleep(delay_secs)

        """ print("Ausschalten des zweiten Relais-Paares...")
        self.relay_board.set_many(second_pair, False) """

        print("Initialisierungssequenz abgeschlossen.")
