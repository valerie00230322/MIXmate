# Model/recipe_model.py
import sqlite3
from pathlib import Path


class RecipeModel:
    def __init__(self, db_filename="mixmate-oida.db"):
        # DB im Model-Ordner
        self.db_path = Path(__file__).resolve().parent / db_filename
        self._init_db()
        # Nur Seeding, keine JSON-Migration
        self._seed_demo_data_if_empty()

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

            --------------------------------------------------------------------
            -- Pumpen & Zuordnungen
            --------------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS Pumps (
                pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                channel INTEGER NOT NULL CHECK (channel BETWEEN 1 AND 5),
                flow_ml_per_s REAL NOT NULL DEFAULT 1.0 CHECK (flow_ml_per_s > 0)
            );

            CREATE TABLE IF NOT EXISTS PumpAssignments (
                ingredient_id INTEGER NOT NULL UNIQUE,
                pump_id INTEGER NOT NULL,
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE CASCADE,
                FOREIGN KEY (pump_id)      REFERENCES Pumps(pump_id) ON DELETE RESTRICT
            );
            """)
            conn.commit()

    # ---------------- Demo-Seeding (ohne JSON) ----------------
    def _seed_demo_data_if_empty(self) -> None:
        """
        Befüllt die DB beim ersten Start mit Demo-Cocktails, Pumpen & Zuordnungen.
        Idempotent: existierende Einträge bleiben unberührt.
        """
        with self._connect() as conn:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM Cocktails;")
            n_cocktails = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM Pumps;")
            n_pumps = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM PumpAssignments;")
            n_assign = cur.fetchone()[0]

        # 1) Cocktails + Zutaten nur einmalig anlegen
        if n_cocktails == 0:
            demo_recipes = [
                {
                    "name": "Daiquiri",
                    "ingredients": [
                        {"name": "Rum",           "amount_ml": 60},
                        {"name": "Limettensaft",  "amount_ml": 30},
                        {"name": "Zuckersirup",   "amount_ml": 15},
                    ],
                },
                {
                    "name": "Gin Tonic",
                    "ingredients": [
                        {"name": "Gin",          "amount_ml": 50},
                        {"name": "Tonic Water",  "amount_ml": 120},
                    ],
                },
                {
                    "name": "Gimlet",
                    "ingredients": [
                        {"name": "Gin",           "amount_ml": 60},
                        {"name": "Limettensaft",  "amount_ml": 15},
                        {"name": "Zuckersirup",   "amount_ml": 15},
                    ],
                },
            ]
            self.save_recipes(demo_recipes)
            print("Demo-Cocktails eingespielt.")

        # 2) 5 Pumpen (Kanäle 1..5) mit groben Flow-Raten
        if n_pumps == 0:
            self.upsert_pump(name="Pump Rum",        channel=1, flow_ml_per_s=18.0)
            self.upsert_pump(name="Pump Limette",    channel=2, flow_ml_per_s=20.0)
            self.upsert_pump(name="Pump Sirup",      channel=3, flow_ml_per_s=15.0)
            self.upsert_pump(name="Pump Gin",        channel=4, flow_ml_per_s=18.0)
            self.upsert_pump(name="Pump TonicWater", channel=5, flow_ml_per_s=25.0)
            print("Demo-Pumpen (Kanäle 1–5) angelegt.")

        # 3) Zuordnungen (Zutat -> Pumpe)
        if n_assign == 0:
            mapping = {
                "Rum":          "Pump Rum",
                "Limettensaft": "Pump Limette",
                "Zuckersirup":  "Pump Sirup",
                "Gin":          "Pump Gin",
                "Tonic Water":  "Pump TonicWater",
            }
            # gezielt mappen (falls Zutaten/Pumpen existieren)
            assigned = 0
            for ing_name, pump_name in mapping.items():
                try:
                    self.set_pump_for_ingredient(ingredient_name=ing_name, pump_name=pump_name)
                    assigned += 1
                except Exception:
                    pass

            # Fallback: falls immer noch keine einzige Zuordnung existiert,
            # ordne alphabetisch die ersten 5 Zutaten den Kanälen 1..5 zu.
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM PumpAssignments;")
                now_assign = cur.fetchone()[0]
                if now_assign == 0:
                    cur.execute("SELECT ingredient_id, name FROM Ingredients ORDER BY name LIMIT 5;")
                    ingredients = cur.fetchall()
                    for idx, row in enumerate(ingredients, start=1):
                        cur.execute("SELECT pump_id FROM Pumps WHERE channel=?", (idx,))
                        prow = cur.fetchone()
                        if not prow:
                            continue
                        cur.execute(
                            "INSERT OR IGNORE INTO PumpAssignments (ingredient_id, pump_id) VALUES (?, ?)",
                            (row["ingredient_id"], prow["pump_id"])
                        )
                    conn.commit()
                    print("Demo-Zuordnungen (alphabetisch 1:1 auf Kanäle 1–5) erstellt.")
                elif assigned > 0:
                    print(f"{assigned} Demo-Zuordnungen gesetzt.")

    # ---------------- Öffentliche API ----------------
    def load_recipes(self):
        """[{ "name": str, "ingredients": [{ "name": str, "amount_ml": float }, ...] }, ...]"""
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
        """Fügt Cocktails/Zutaten hinzu bzw. aktualisiert Mengen (kein Full-Replace)."""
        with self._connect() as conn:
            cur = conn.cursor()
            for r in recipes:
                cur.execute("INSERT OR IGNORE INTO Cocktails (name) VALUES (?)", (r["name"],))
                cur.execute("SELECT cocktail_id FROM Cocktails WHERE name = ?", (r["name"],))
                cocktail_id = cur.fetchone()["cocktail_id"]

                for ing in r.get("ingredients", []):
                    ing_name = ing["name"]
                    amount = float(ing.get("amount_ml", 0))

                    cur.execute("INSERT OR IGNORE INTO Ingredients (name) VALUES (?)", (ing_name,))
                    cur.execute("SELECT ingredient_id FROM Ingredients WHERE name = ?", (ing_name,))
                    ingredient_id = cur.fetchone()["ingredient_id"]

                    cur.execute("""
                        INSERT INTO CocktailIngredients (cocktail_id, ingredient_id, quantity_required)
                        VALUES (?, ?, ?)
                        ON CONFLICT(cocktail_id, ingredient_id)
                        DO UPDATE SET quantity_required=excluded.quantity_required;
                    """, (cocktail_id, ingredient_id, amount))
            conn.commit()

    def get_recipe_by_name(self, name):
        name_lc = (name or "").lower()
        for r in self.load_recipes():
            if r["name"].lower() == name_lc:
                return r
        return None

    def add_recipe(self, recipe):
        self.save_recipes([recipe])

    def delete_recipe(self, name):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM Cocktails WHERE name = ?", (name,))
            conn.commit()

    # ---------------- Pumpen / Zuordnungen ----------------
    def list_pumps(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT pump_id, name, channel, flow_ml_per_s FROM Pumps ORDER BY channel;")
            return [dict(r) for r in cur.fetchall()]

    def upsert_pump(self, *, name: str, channel: int, flow_ml_per_s: float = 20.0):
        if not (1 <= int(channel) <= 5):
            raise ValueError("channel muss 1..5 sein")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO Pumps (name, channel, flow_ml_per_s)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE
                SET channel=excluded.channel, flow_ml_per_s=excluded.flow_ml_per_s
            """, (name, int(channel), float(flow_ml_per_s)))
            conn.commit()

    def set_pump_for_ingredient(self, *, ingredient_name: str, pump_name: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ingredient_id FROM Ingredients WHERE name=?", (ingredient_name,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Unbekannte Zutat: {ingredient_name}")
            ingredient_id = row["ingredient_id"]

            cur.execute("SELECT pump_id FROM Pumps WHERE name=?", (pump_name,))
            prow = cur.fetchone()
            if not prow:
                raise ValueError(f"Unbekannte Pumpe: {pump_name}")
            pump_id = prow["pump_id"]

            cur.execute("""
                INSERT INTO PumpAssignments (ingredient_id, pump_id)
                VALUES (?, ?)
                ON CONFLICT(ingredient_id) DO UPDATE SET pump_id=excluded.pump_id
            """, (ingredient_id, pump_id))
            conn.commit()

    def get_dispense_plan(self, cocktail_name: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT cocktail_id FROM Cocktails WHERE name=?", (cocktail_name,))
            c = cur.fetchone()
            if not c:
                return None
            cocktail_id = c["cocktail_id"]

            cur.execute("""
                SELECT i.name AS ingredient,
                       ci.quantity_required AS amount_ml,
                       pa.pump_id AS pump_id,
                       p.channel AS pump_channel,
                       p.flow_ml_per_s AS flow_ml_per_s
                FROM CocktailIngredients ci
                JOIN Ingredients i ON i.ingredient_id = ci.ingredient_id
                LEFT JOIN PumpAssignments pa ON pa.ingredient_id = i.ingredient_id
                LEFT JOIN Pumps p ON p.pump_id = pa.pump_id
                WHERE ci.cocktail_id = ?
                ORDER BY i.name;
            """, (cocktail_id,))
            steps = [dict(row) for row in cur.fetchall()]
            return steps
