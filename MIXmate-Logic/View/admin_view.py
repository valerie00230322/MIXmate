class AdminView:
    def __init__(self, admin_controller, pump_controller):
        self.admin_controller = admin_controller
        self.pump_controller = pump_controller

    def run(self):
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
        while True:
            print("\n--- Zutaten ---")
            print("1) Anzeigen")
            print("2) Hinzufügen")
            print("3) Umbenennen")
            print("4) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                items = self.admin_controller.list_ingredients()
                for ing in items:
                    print(f"{ing['ingredient_id']}: {ing['name']}")

            elif c == "2":
                name = input("Zutatenname: ").strip()
                try:
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
        while True:
            print("\n--- Cocktails ---")
            print("1) Anzeigen")
            print("2) Hinzufügen")
            print("3) Löschen")
            print("4) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                items = self.admin_controller.list_cocktails()
                for co in items:
                    print(f"{co['cocktail_id']}: {co['cocktail_name']}")
            elif c == "2":
                name = input("Cocktailname: ").strip()
                self.admin_controller.add_cocktail(name)
                print("Gespeichert.")
            elif c == "3":
                cocktail_id = int(input("cocktail_id löschen: ").strip())
                self.admin_controller.delete_cocktail(cocktail_id)
                print("Gelöscht.")
            elif c == "4":
                return
            else:
                print("Ungültige Eingabe")

    def pumps_menu(self):
        while True:
            print("\n--- Pumpen (Admin) ---")
            print("1) Anzeigen")
            print("2) Neue Pumpe anlegen")
            print("3) Pumpe löschen")
            print("4) Zutat zuweisen (mit Zutatenliste)")
            print("5) Zurück")

            c = input("Auswahl: ").strip()

            if c == "1":
                pumps = self.pump_controller.list_pumps()
                for p in pumps:
                    print(
                        f"Pumpe {p['pump_number']}: ingredient_id={p['ingredient_id']}, "
                        f"flow_rate_ml_s={p['flow_rate_ml_s']}, position_steps={p['position_steps']}"
                    )

            elif c == "2":
                pump_number = int(input("Neue pump_number: ").strip())
                self.admin_controller.add_pump(pump_number)
                print("Pumpe angelegt. Position/Flow-Rate machst du dann in der Kalibrierung.")

            elif c == "3":
                pump_number = int(input("pump_number löschen: ").strip())
                self.admin_controller.delete_pump(pump_number)
                print("Pumpe gelöscht.")

            elif c == "4":
                pump_number = int(input("Pumpennummer: ").strip())

                ingredients = self.admin_controller.list_ingredients()
                for ing in ingredients:
                    print(f"{ing['ingredient_id']}: {ing['name']}")

                ingredient_id = int(input("ingredient_id wählen: ").strip())
                self.pump_controller.assign_ingredient(pump_number, ingredient_id)
                print("Gespeichert.")

            elif c == "5":
                return

            else:
                print("Ungültige Eingabe")
