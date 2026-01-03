class AdminView:
    def __init__(self, admin_controller, pump_controller):
        # AdminController: alles rund um DB-Stammdaten (Zutaten, Cocktails, Rezepte)
        # PumpController: Pumpen anzeigen / Zutat zuweisen (und Kalibrierung später)
        self.admin_controller = admin_controller
        self.pump_controller = pump_controller

    def run(self):
        # Hauptmenü für den Admin-Bereich
        while True:
            print("\n=== ADMIN ===")
            print("1) Zutaten verwalten")
            print("2) Cocktails verwalten")
            print("3) Pumpen verwalten")
            print("4) Zurück")

            choice = input("Auswahl: ").strip()

            if choice == "1":
                self.ingredients_menu()
            elif choice == "2":
                self.cocktails_menu()
            elif choice == "3":
                self.pumps_menu()
            elif choice == "4":
                return
            else:
                print("Ungültige Eingabe")

    def ingredients_menu(self):
        # Zutaten sind bei euch eher Stammdaten: anzeigen, hinzufügen, umbenennen
        while True:
            print("\n--- Zutaten ---")
            print("1) Anzeigen")
            print("2) Hinzufügen")
            print("3) Umbenennen")
            print("4) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                try:
                    items = self.admin_controller.list_ingredients()
                    for ing in items:
                        print(f"{ing['ingredient_id']}: {ing['name']}")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "2":
                try:
                    name = input("Zutatenname: ").strip()
                    self.admin_controller.add_ingredient(name)
                    print("Gespeichert.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "3":
                try:
                    ingredient_id = int(input("ingredient_id umbenennen: ").strip())
                    new_name = input("Neuer Name: ").strip()
                    self.admin_controller.rename_ingredient(ingredient_id, new_name)
                    print("Umbenannt.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "4":
                return
            else:
                print("Ungültige Eingabe")

    def cocktails_menu(self):
        # Hier verwaltest du Cocktails (Name/ID) und kannst danach das Rezept bearbeiten.
        while True:
            print("\n--- Cocktails ---")
            print("1) Anzeigen")
            print("2) Hinzufügen")
            print("3) Löschen")
            print("4) Rezept bearbeiten")
            print("5) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                try:
                    items = self.admin_controller.list_cocktails()
                    for co in items:
                        # Achte darauf: dein Model muss "cocktail_name" zurückgeben
                        print(f"{co['cocktail_id']}: {co['cocktail_name']}")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "2":
                try:
                    name = input("Cocktailname: ").strip()
                    new_id = self.admin_controller.add_cocktail(name)
                    # Falls add_cocktail keine ID zurückgibt, kannst du das einfach weglassen
                    if new_id is not None:
                        print(f"Gespeichert. Neue cocktail_id: {new_id}")
                    else:
                        print("Gespeichert.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "3":
                try:
                    cocktail_id = int(input("cocktail_id löschen: ").strip())
                    self.admin_controller.delete_cocktail(cocktail_id)
                    print("Gelöscht.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "4":
                try:
                    cocktail_id = int(input("cocktail_id für Rezeptbearbeitung: ").strip())
                    self.recipes_menu(cocktail_id)
                except Exception as e:
                    print("Fehler:", e)

            elif c == "5":
                return
            else:
                print("Ungültige Eingabe")

    def recipes_menu(self, cocktail_id: int):
        # Das ist das Rezept-Menü für genau einen Cocktail.
        # Du setzt order_index bewusst manuell -die Reihenfolge wird selbst manuell bestimmt
        while True:
            print(f"\n--- Rezept bearbeiten (cocktail_id={cocktail_id}) ---")
            print("1) Rezept anzeigen")
            print("2) Zutat hinzufügen")
            print("3) Zutat ändern (ml / order_index)")
            print("4) Zutat entfernen")
            print("5) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                try:
                    recipe = self.admin_controller.get_recipe(cocktail_id)
                    if not recipe:
                        print("Rezept ist leer.")
                    else:
                        for r in recipe:
                            print(
                                f"{r['order_index']}. {r['ingredient_name']} "
                                f"(ingredient_id={r['ingredient_id']}): {r['amount_ml']} ml"
                            )
                except Exception as e:
                    print("Fehler:", e)

            elif c == "2":
                try:
                    # alle Zutaten anzeigen zur Auswahl
                    print("\nZutatenliste:")
                    ingredients = self.admin_controller.list_ingredients()
                    for ing in ingredients:
                        print(f"{ing['ingredient_id']}: {ing['name']}")

                    ingredient_id = int(input("ingredient_id wählen: ").strip())
                    amount_ml = float(input("Menge in ml: ").strip())
                    order_index = int(input("Reihenfolge (order_index): ").strip())

                    self.admin_controller.add_recipe_item(cocktail_id, ingredient_id, amount_ml, order_index)
                    print("Hinzugefügt.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "3":
                try:
                    ingredient_id = int(input("ingredient_id ändern: ").strip())
                    amount_ml = float(input("Neue Menge in ml: ").strip())
                    order_index = int(input("Neuer order_index: ").strip())

                    self.admin_controller.update_recipe_item(cocktail_id, ingredient_id, amount_ml, order_index)
                    print("Aktualisiert.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "4":
                try:
                    ingredient_id = int(input("ingredient_id entfernen: ").strip())
                    self.admin_controller.delete_recipe_item(cocktail_id, ingredient_id)
                    print("Entfernt.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "5":
                return
            else:
                print("Ungültige Eingabe")

    def pumps_menu(self):
        # Pumpen im Admin-Menü: anlegen/löschen und Zutaten zuweisen.
        # Position und Flow-Rate testest du am besten im Kalibrierungsmenü, weil das Hardware ist.
        while True:
            print("\n--- Pumpen (Admin) ---")
            print("1) Anzeigen")
            print("2) Neue Pumpe anlegen")
            print("3) Pumpe löschen")
            print("4) Zutat zuweisen (mit Zutatenliste)")
            print("5) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                try:
                    pumps = self.pump_controller.list_pumps()
                    for p in pumps:
                        print(
                            f"Pumpe {p['pump_number']}: ingredient_id={p['ingredient_id']}, "
                            f"flow_rate_ml_s={p['flow_rate_ml_s']}, position_steps={p['position_steps']}"
                        )
                except Exception as e:
                    print("Fehler:", e)

            elif c == "2":
                try:
                    pump_number = int(input("Neue pump_number: ").strip())
                    self.admin_controller.add_pump(pump_number)
                    print("Pumpe angelegt. Position/Flow-Rate machst du dann in der Kalibrierung.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "3":
                try:
                    pump_number = int(input("pump_number löschen: ").strip())
                    self.admin_controller.delete_pump(pump_number)
                    print("Pumpe gelöscht.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "4":
                try:
                    pump_number = int(input("Pumpennummer: ").strip())

                    ingredients = self.admin_controller.list_ingredients()
                    for ing in ingredients:
                        print(f"{ing['ingredient_id']}: {ing['name']}")

                    ingredient_id = int(input("ingredient_id wählen: ").strip())

                    # Zuweisung ist ein DB-Mapping. Du machst es hier über den PumpController,
                    # weil du dort bereits assign_ingredient() hast.
                    self.pump_controller.assign_ingredient(pump_number, ingredient_id)
                    print("Gespeichert.")
                except Exception as e:
                    print("Fehler:", e)

            elif c == "5":
                return
            else:
                print("Ungültige Eingabe")
