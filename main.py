from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
import threading
import time
import json
import pymysql

class CocktailLogic:
    def __init__(self, cocktails):
        self.cocktails = cocktails

    def mix_cocktail(self, name, finished_callback):
        "Startet den Mixvorgang in einem Thread."
        thread = threading.Thread(target=self._simulate_mixing, args=(name, finished_callback), daemon=True)
        thread.start()

    def _simulate_mixing(self, name, finished_callback):
        "Simuliert das Pumpen der Zutaten."
        zutaten = self.cocktails[name]
        for zutat, sekunden in zutaten.items():
            print(f"[SIM] Pumpe {zutat} für {sekunden} Sekunden.")
            time.sleep(sekunden)

        # UI-Update im Hauptthread
        Clock.schedule_once(lambda dt: finished_callback(name))


class CocktailApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"

        self.load_cocktails()
        self.logic = CocktailLogic(self.cocktails)

        return Builder.load_file("View/main.kv")

    def load_cocktails(self):
        with open("cocktails.json", "r") as f:
            self.cocktails = json.load(f)

    def on_start(self):
      #"Füllt die Liste mit Cocktails."
        for name in self.cocktails.keys():
            self.root.ids.cocktail_list.add_widget(
                self.create_list_item(name)
            )

    def create_list_item(self, name):
        from kivymd.uix.list import OneLineListItem
        return OneLineListItem(
            text=name,
            on_release=lambda x, n=name: self.start_mixing(n)
        )

    def start_mixing(self, name):
        print(f"Starte Mixvorgang für {name}")
        self.logic.mix_cocktail(name, self.show_finished_snackbar)

    def show_finished_snackbar(self, name):
        snackbar = Snackbar(text=f"{name} ist fertig!")
        snackbar.open()


if __name__ == "__main__":
   CocktailApp().run()
   """  conn = pymysql.connect(
       host="172.21.104.81",  # z. B. 172.20.200.45
       user="cocktailuser",
       password="test123",
       database="cocktaildb" 
   )"""

   """print("Verbindung erfolgreich:", conn.open)
   conn.close()"""
