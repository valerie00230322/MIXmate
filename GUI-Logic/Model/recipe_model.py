import sqlite3
from pathlib import Path
import os

# Basispfad ist der Ordner, in dem die Datei liegt
base_dir = Path(__file__).resolve().parent

# Wir befinden uns schon im "Model"-Ordner, daher direkt den Pfad setzen
db_path = base_dir / "mixmate-oida.db"

# Optional: Ordner anlegen, falls du später von woanders zugreifst
# base_dir.mkdir(parents=True, exist_ok=True)

# Datenbankverbindung herstellen
with sqlite3.connect(db_path) as conn:
    conn.execute("PRAGMA foreign_keys = ON;")  # Fremdschlüssel aktivieren
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Tabellen erstellen
    cursor.executescript('''
        -- Zutaten-Tabelle
        CREATE TABLE IF NOT EXISTS Ingredients (
            ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            quantity_available DECIMAL(10, 2) DEFAULT 0
        );

        -- Cocktails-Tabelle
        CREATE TABLE IF NOT EXISTS Cocktails (
            cocktail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT
        );

        -- Cocktail-Zutaten-Verknüpfungstabelle
        CREATE TABLE IF NOT EXISTS CocktailIngredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cocktail_id INTEGER,
            ingredient_id INTEGER,
            quantity_required DECIMAL(10, 2) NOT NULL CHECK (quantity_required > 0),
            FOREIGN KEY (cocktail_id) REFERENCES Cocktails(cocktail_id) ON DELETE RESTRICT,
            FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE RESTRICT
        );
    ''')

    conn.commit()
