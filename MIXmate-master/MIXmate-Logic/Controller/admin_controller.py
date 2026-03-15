from Model.cocktail_model import CocktailModel
from Model.ingredient_model import IngredientModel
from Model.level_model import LevelModel
from Model.pump_model import PumpModel
from Model.system_settings_model import SystemSettingsModel

class AdminController:
    def __init__(self, db_path=None):
        # Modelle für DB-Zugriff
        self.cocktail_model = CocktailModel(db_path=db_path)
        self.ingredient_model = IngredientModel(db_path=db_path)
        self.pump_model = PumpModel(db_path=db_path)
        self.level_model = LevelModel(db_path=db_path)
        self.settings_model = SystemSettingsModel(db_path=db_path)

    # Zutaten

    def list_ingredients(self):
        # Alle Zutaten aus der DB holen
        return self.ingredient_model.get_all_ingredients()

    def add_ingredient(self, name: str):
        # Neue Zutat speichern
        self.ingredient_model.add_ingredient(name)

    def rename_ingredient(self, ingredient_id: int, new_name: str):
        # Zutat umbenennen
        self.ingredient_model.rename_ingredient(ingredient_id, new_name)

    # Cocktails

    def list_cocktails(self):
        # Alle Cocktails aus der DB holen
        return self.cocktail_model.get_all_cocktails()

    def add_cocktail(self, cocktail_name: str):
        # Neuen Cocktail speichern
        self.cocktail_model.add_cocktail(cocktail_name)
        return None

    def delete_cocktail(self, cocktail_id: int):
        # Cocktail und Rezeptzeilen löschen
        self.cocktail_model.delete_cocktail(cocktail_id)

    def rename_cocktail(self, cocktail_id: int, new_name: str):
        # Cocktail umbenennen
        self.cocktail_model.rename_cocktail(cocktail_id, new_name)

    # Rezepte

    def get_recipe(self, cocktail_id: int):
        # Rezept eines Cocktails anzeigen
        return self.cocktail_model.get_recipe(cocktail_id)

    def add_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        # Zutat ins Rezept einfügen
        self.cocktail_model.add_recipe_item(cocktail_id, ingredient_id, amount_ml, order_index)

    def update_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        # Rezeptzeile ändern (Menge/Reihenfolge)
        self.cocktail_model.update_recipe_item(cocktail_id, ingredient_id, amount_ml, order_index)

    def delete_recipe_item(self, cocktail_id: int, ingredient_id: int):
        # Zutat aus Rezept entfernen
        self.cocktail_model.delete_recipe_item(cocktail_id, ingredient_id)

    # Pumpen

    def add_pump(self, pump_number: int):
        # Neue Pumpe mit Standardwerten anlegen; Kalibrierung folgt danach.
        self.pump_model.add_pump(pump_number=pump_number, flow_rate_ml_s=1.0, position_steps=0)

    def delete_pump(self, pump_number: int):
        # Pumpe löschen
        self.pump_model.delete_pump(pump_number)

    def set_pump_distance(self, pump_number: int, distance_mm: int):
        # Historischer Methodenname beibehalten, Einheit ist mm.
        if distance_mm < 0:
            raise ValueError("distance_mm muss >= 0 sein")

        self.pump_model.update_position_mm(pump_number, int(distance_mm))
        self.settings_model.set_pump_distance(pump_number, int(distance_mm))

    # Ebenen / Rezept-Quelle

    def list_levels(self):
        return self.level_model.get_all_levels()

    def add_level(self, extension_distance_mm: float = 0.0):
        if float(extension_distance_mm) < 0:
            raise ValueError("extension_distance_mm muss >= 0 sein")
        return self.level_model.add_level_auto(float(extension_distance_mm))

    def delete_level(self, levelnumber: int):
        self.level_model.delete_level(int(levelnumber))

    def set_level_height(self, levelnumber: int, height_mm: float):
        if float(height_mm) < 0:
            raise ValueError("height_mm muss >= 0 sein")
        self.settings_model.set_level_height(levelnumber, float(height_mm))

    def get_level_height(self, levelnumber: int):
        return self.settings_model.get_level_height(levelnumber)

    def set_level_ausschub_distance(self, levelnumber: int, ausschub_distance_mm: float):
        if float(ausschub_distance_mm) < 0:
            raise ValueError("ausschub_distance_mm muss >= 0 sein")
        self.settings_model.set_level_ausschub_distance(levelnumber, float(ausschub_distance_mm))

    def get_level_ausschub_distance(self, levelnumber: int):
        return self.settings_model.get_level_ausschub_distance(levelnumber)

    def set_level_direction(self, levelnumber: int, forward: bool):
        self.settings_model.set_level_direction(levelnumber, bool(forward))

    def get_level_direction(self, levelnumber: int):
        return self.settings_model.get_level_direction(levelnumber)

    def set_cocktail_source_level(self, cocktail_id: int, levelnumber: int):
        self.settings_model.set_cocktail_source_level(cocktail_id, int(levelnumber))

    def get_cocktail_source_level(self, cocktail_id: int):
        return self.settings_model.get_cocktail_source_level(cocktail_id)

    # Globale Maschinenparameter

    def set_mixer_height(self, mixer_height_mm: float):
        if float(mixer_height_mm) < 0:
            raise ValueError("mixer_height_mm muss >= 0 sein")
        self.settings_model.set_mixer_height(float(mixer_height_mm))

    def get_mixer_height(self):
        return self.settings_model.get_mixer_height()

    def set_mixer_ausschub_distance(self, distance_mm: float):
        if float(distance_mm) < 0:
            raise ValueError("mixer_ausschub_distance_mm muss >= 0 sein")
        self.settings_model.set_mixer_ausschub_distance(float(distance_mm))

    def get_mixer_ausschub_distance(self):
        return self.settings_model.get_mixer_ausschub_distance()

    def set_mixer_direction(self, left: bool):
        self.settings_model.set_mixer_direction(bool(left))

    def get_mixer_direction(self):
        return self.settings_model.get_mixer_direction()

    def set_waiting_position(self, waiting_position_mm: float):
        if float(waiting_position_mm) < 0:
            raise ValueError("waiting_position_mm muss >= 0 sein")
        self.settings_model.set_waiting_position(float(waiting_position_mm))

    def get_waiting_position(self):
        return self.settings_model.get_waiting_position()

    def set_load_unload_position(self, position_mm: float):
        if float(position_mm) < 0:
            raise ValueError("load_unload_position_mm muss >= 0 sein")
        self.settings_model.set_load_unload_position(float(position_mm))

    def get_load_unload_position(self):
        return self.settings_model.get_load_unload_position()

    def set_homing_safe_height(self, height_mm: float):
        if float(height_mm) < 0:
            raise ValueError("homing_safe_height_mm muss >= 0 sein")
        self.settings_model.set_homing_safe_height(float(height_mm))

    def get_homing_safe_height(self):
        return self.settings_model.get_homing_safe_height()

    def set_ausschub_distance(self, ausschub_distance_mm: float):
        if float(ausschub_distance_mm) < 0:
            raise ValueError("ausschub_distance_mm muss >= 0 sein")
        self.settings_model.set_ausschub_distance(float(ausschub_distance_mm))

    def get_ausschub_distance(self):
        return self.settings_model.get_ausschub_distance()

    def set_simulation_mode(self, enabled: bool):
        self.settings_model.set_simulation_mode(bool(enabled))

    def get_simulation_mode(self) -> bool:
        return self.settings_model.get_simulation_mode()
