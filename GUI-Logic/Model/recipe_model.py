import sqlite3
from pathlib import Path
import json


class RecipeModel:
    def __init__(self, db_filename="mixmate-oida.db", legacy_json="recipes.json"):
        # DB im Model-Ordner
        self.db_path = Path(__file__).resolve().parent / db_filename
        self.legacy_json_path = Path(__file__).resolve().parent / legacy_json
        self._init_db()
        self._migrate_from_legacy_json_if_present()

    # ---------------- Internals ----------------
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS Ingredients (
                ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                quantity_available DECIMAL(10,2) DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Cocktails (
                cocktail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS CocktailIngredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cocktail_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity_required DECIMAL(10,2) NOT NULL CHECK (quantity_required > 0),
                FOREIGN KEY (cocktail_id) REFERENCES Cocktails(cocktail_id) ON DELETE RESTRICT,
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE RESTRICT
            );

            -- verhindert doppelte (cocktail_id, ingredient_id)
            CREATE UNIQUE INDEX IF NOT EXISTS ux_cocktail_ingredient
            ON CocktailIngredients(cocktail_id, ingredient_id);
            """)
            conn.commit()

    def _migrate_from_legacy_json_if_present(self):
        """Falls noch eine recipes.json existiert, einmalig in die DB übernehmen."""
        if self.legacy_json_path.exists():
            try:
                with self.legacy_json_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Nur migrieren, wenn DB leer ist:
                with self._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM Cocktails;")
                    if cur.fetchone()[0] == 0:
                        self.save_recipes(data)
                        print(f"✅ Rezepte aus {self.legacy_json_path.name} migriert.")
            except Exception as e:
                print(f"⚠️ Fehler bei JSON-Migration: {e}")

    # ---------------- Öffentliche API ----------------
    def load_recipes(self):
        """Gibt eine Liste wie früher zurück:
        [{ "name": str, "ingredients": [{ "name": str, "amount_ml": float }, ...] }, ...]
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT cocktail_id, name FROM Cocktails ORDER BY name;")
            cocktails = []
            for c in cur.fetchall():
                cur.execute("""
                    SELECT i.name, ci.quantity_required AS amount_ml
                    FROM CocktailIngredients ci
                    JOIN Ingredients i ON i.ingredient_id = ci.ingredient_id
                    WHERE ci.cocktail_id = ?
                    ORDER BY i.name;
                """, (c["cocktail_id"],))
                ingredients = [dict(row) for row in cur.fetchall()]
                cocktails.append({"name": c["name"], "ingredients": ingredients})
            return cocktails

    def save_recipes(self, recipes):
        """Ersetzt NICHT die DB, sondern fügt hinzu/aktualisiert (wie vorher).
        Erwartet dieselbe Struktur wie dein altes JSON.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            for r in recipes:
                # Cocktail anlegen (falls neu)
                cur.execute("INSERT OR IGNORE INTO Cocktails (name) VALUES (?)", (r["name"],))
                cur.execute("SELECT cocktail_id FROM Cocktails WHERE name = ?", (r["name"],))
                cocktail_id = cur.fetchone()["cocktail_id"]

                # Zutaten + Zuordnung
                for ing in r.get("ingredients", []):
                    ing_name = ing["name"]
                    amount = float(ing.get("amount_ml", 0))

                    cur.execute("INSERT OR IGNORE INTO Ingredients (name) VALUES (?)", (ing_name,))
                    cur.execute("SELECT ingredient_id FROM Ingredients WHERE name = ?", (ing_name,))
                    ingredient_id = cur.fetchone()["ingredient_id"]

                    # upsert über UNIQUE-Index (cocktail_id, ingredient_id)
                    cur.execute("""
                        INSERT INTO CocktailIngredients (cocktail_id, ingredient_id, quantity_required)
                        VALUES (?, ?, ?)
                        ON CONFLICT(cocktail_id, ingredient_id)
                        DO UPDATE SET quantity_required=excluded.quantity_required;
                    """, (cocktail_id, ingredient_id, amount))
            conn.commit()

    def get_recipe_by_name(self, name):
        """Gibt ein einzelnes Rezept anhand des Namens zurück."""
        name_lc = (name or "").lower()
        for r in self.load_recipes():
            if r["name"].lower() == name_lc:
                return r
        return None

    def add_recipe(self, recipe):
        """Fügt ein einzelnes Rezept hinzu (wie bisher)."""
        self.save_recipes([recipe])

    def delete_recipe(self, name):
        """Löscht einen Cocktail anhand des Namens."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM Cocktails WHERE name = ?", (name,))
            conn.commit()

    # ----------------------------------------------------------
    # JSON Import / Export
    # ----------------------------------------------------------
    def export_recipes_to_json(self, out_path: Path | None = None) -> Path:
        """
        Exportiert alle Rezepte aus der DB in eine JSON-Datei.
        Standard: Model/recipes.json (self.legacy_json_path)
        Rückgabe: Pfad zur geschriebenen Datei.
        """
        if out_path is None:
            out_path = self.legacy_json_path

        data = self.load_recipes()
        out_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"✅ Rezepte exportiert nach: {out_path}")
        return out_path

    def import_recipes_from_json(self, in_path: Path | None = None, replace: bool = False) -> None:
        """
        Importiert Rezepte aus einer JSON-Datei in die DB.
        - Standard: Model/recipes.json (self.legacy_json_path)
        - replace=True: löscht vorher alle Cocktails & Zuordnungen (Ingredients bleiben bestehen)
        """
        if in_path is None:
            in_path = self.legacy_json_path
        if not in_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {in_path}")

        data = json.loads(in_path.read_text(encoding="utf-8"))

        if replace:
            with self._connect() as conn:
                conn.execute("DELETE FROM CocktailIngredients;")
                conn.execute("DELETE FROM Cocktails;")
                conn.commit()

        self.save_recipes(data)
        print(f"✅ Rezepte importiert von: {in_path}")
