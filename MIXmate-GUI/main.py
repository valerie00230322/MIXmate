from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from Controller.mix_controller import MixController

class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = MixController()

    def mix_button_pressed(self):
        self.controller.mix_cocktail(1)

class MixApp(App):
    def build(self):
        Builder.load_file("View/mixapp.kv")   # <-- wichtig!
        return MainScreen()

if __name__ == "__main__":
    MixApp().run()
