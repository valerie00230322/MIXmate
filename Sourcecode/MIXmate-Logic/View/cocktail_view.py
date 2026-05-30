class CocktailView:
    def __init__(self, mix_controller):
        self.mix_controller = mix_controller

    def run_mix_flow(self):
        # Einfache Eingabe per Cocktail-ID.
        # Controller uebernimmt Rezeptsuche und Mixstart.
        raw = input("Cocktail-ID eingeben: ").strip()
        cocktail_id = int(raw)

        recipe = self.mix_controller.mix_cocktail(cocktail_id)

        print("\nCocktail-Rezept:\n")
        for item in recipe:
            print(f"- {item}")

        return recipe
