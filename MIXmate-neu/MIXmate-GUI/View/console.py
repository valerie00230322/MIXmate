from Controller.mix_controller import MixController

class ConsoleView:
    def __init__(self):
        self.controller = MixController()

    def run(self):
        print("=== MIXMATE Console View ===")
        print("1) Cocktail mischen")
        print("2) Exit")

        choice = input("Auswahl: ")

        if choice == "1":
            self.mix_cocktail()
        else:
            print("Bye!")

    def mix_cocktail(self):
        cocktail_id = input("Cocktail-ID eingeben: ")

        try:
            recipe = self.controller.mix_cocktail(int(cocktail_id))
        except Exception as e:
            print("Fehler:", e)
            return

        print("\nCocktail-Rezept gefunden:\n")
        for item in recipe:
            print(f"- {item}")

if __name__ == "__main__":
    ConsoleView().run()
