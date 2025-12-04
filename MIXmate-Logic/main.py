from Controller.mix_controller import MixController
from View.console import ConsoleView
import sys

class MIXmate:
    def __init__(self):
        self.controller = MixController()
        self.view = ConsoleView(self.controller)