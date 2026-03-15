import sys

# --- Konsole starten ---
def start_console():
    from View.console import ConsoleView
    ConsoleView().run()


# --- GUI starten ---
# def start_gui():
#     from kivy.app import App
#     from kivy.lang import Builder
#     from kivy.uix.boxlayout import BoxLayout
#     from Controller.mix_controller import MixController

#     class MainScreen(BoxLayout):
#         def __init__(self, **kwargs):
#             super().__init__(**kwargs)
#             self.controller = MixController()

#         def mix_button_pressed(self):
#             self.controller.mix_cocktail(1)

#     class MixApp(App):
#         def build(self):
#             Builder.load_file("View/mixapp.kv")
#             return MainScreen()

#     MixApp().run()


# --- Hauptlogik ---
#if __name__ == "__main__":
    # Startmodus prüfen:
    # python main.py → GUI
    # python main.py console → Konsole
    # if len(sys.argv) > 1 and sys.argv[1].lower() == "console":
    #     start_console()
    # else:
    #     start_gui()
from View.console import ConsoleView

if __name__ == "__main__":
    ConsoleView().run()
