import os
import sqlite3
from Model.db_seed_data import (
    SEED_COCKTAIL_INGREDIENTS,
    SEED_COCKTAILS,
    SEED_INGREDIENTS,
    SEED_LEVELS,
    SEED_MACHINE_PARAMETERS,
    SEED_PUMPS,
)


def ensure_database(db_path: str) -> None:
    # SQLite-Grundstruktur bei Bedarf erstellen.
    if not db_path:
        # Ohne Pfad waere die Datenbankposition nicht nachvollziehbar.
        raise ValueError("db_path darf nicht leer sein")

    db_dir = os.path.dirname(db_path)
    if db_dir:
        # Datenbankordner bei frischer Installation anlegen.
        os.makedirs(db_dir, exist_ok=True)

    con = sqlite3.connect(db_path)
    try:
        # Foreign Keys muessen in SQLite pro Verbindung aktiviert werden.
        con.execute("PRAGMA foreign_keys = ON")
        # Tabellen werden idempotent erstellt.
        con.executescript(
            """
            -- Zutaten-Stammdaten fuer Pumpenzuordnung und Rezepte.
            CREATE TABLE IF NOT EXISTS ingredients (
                -- Technischer Schluessel fuer Fremdschluesselbeziehungen.
                ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Anzeigename der Zutat im Adminbereich.
                name TEXT NOT NULL
            );

            -- Cocktail-Stammdaten ohne Rezeptdetails.
            CREATE TABLE IF NOT EXISTS cocktails (
                -- Technischer Schluessel fuer Rezept- und Level-Zuordnung.
                cocktail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Anzeigename in der Cocktailauswahl.
                cocktail_name TEXT NOT NULL
            );

            -- Rezeptzeilen: welcher Cocktail braucht welche Zutat in welcher Menge.
            CREATE TABLE IF NOT EXISTS cocktail_ingredients (
                -- Verweis auf den Cocktail.
                cocktail_id INTEGER NOT NULL,
                -- Verweis auf die Zutat.
                ingredient_id INTEGER NOT NULL,
                -- Zielmenge fuer den Pumpenlauf.
                amount_ml REAL NOT NULL CHECK (amount_ml > 0),
                -- Reihenfolge der Dosierung innerhalb eines Cocktails.
                order_index INTEGER NOT NULL CHECK (order_index >= 1),
                -- Eine Zutat darf pro Cocktail nur einmal vorkommen.
                PRIMARY KEY (cocktail_id, ingredient_id),
                -- Jede Reihenfolge darf pro Cocktail nur einmal vergeben sein.
                UNIQUE (cocktail_id, order_index),
                FOREIGN KEY (cocktail_id)
                    REFERENCES cocktails(cocktail_id)
                    ON UPDATE CASCADE
                    ON DELETE CASCADE,
                FOREIGN KEY (ingredient_id)
                    REFERENCES ingredients(ingredient_id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );

            -- Pumpen-Konfiguration mit Kalibrierwert und Position.
            CREATE TABLE IF NOT EXISTS pumps (
                -- Interne ID, getrennt von der sichtbaren Pumpennummer.
                pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Sichtbare Pumpennummer am Geraet.
                pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 10),
                -- Optionale Zutat, die diese Pumpe foerdert.
                ingredient_id INTEGER,
                -- Kalibrierte Foerdermenge pro Sekunde.
                flow_rate_ml_s REAL NOT NULL CHECK (flow_rate_ml_s > 0),
                -- Historischer Name; Wert wird als Millimeterposition verwendet.
                position_steps INTEGER NOT NULL CHECK (position_steps >= 0),
                FOREIGN KEY (ingredient_id)
                    REFERENCES ingredients(ingredient_id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            );

            -- Regalebenen, aus denen Glaeser geholt werden koennen.
            CREATE TABLE IF NOT EXISTS levels (
                -- Fachliche Ebenennummer im Regal.
                levelnumber INTEGER PRIMARY KEY
            );

            -- Flexible Key-Value-Ablage fuer Maschinenparameter.
            CREATE TABLE IF NOT EXISTS machine_parameters (
                -- Sprechender Parametername, z.B. mixer_height_mm.
                param_key TEXT PRIMARY KEY,
                -- Zahlenwert fuer Hoehen, Richtungen, Zuordnungen und Flags.
                param_value REAL NOT NULL
            );
            """
        )
        _seed_database_if_empty(con)
        # Schema und Seed-Daten gemeinsam sichern.
        con.commit()
    finally:
        # Bootstrap-Verbindung nicht offen halten.
        con.close()


def _seed_database_if_empty(con: sqlite3.Connection) -> None:
    # Leere Datenbank mit Startdaten fuellen.
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM ingredients")
    # Zutaten dienen als Marker fuer bereits befuellte Startdaten.
    ingredients_count = int(cur.fetchone()[0])
    if ingredients_count > 0:
        # Vorhandene Datenbank nicht erneut befuellen.
        return

    cur.executemany(
        # Stammdaten zuerst, weil Rezepte darauf referenzieren.
        "INSERT INTO ingredients (ingredient_id, name) VALUES (?, ?)",
        [(x["ingredient_id"], x["name"]) for x in SEED_INGREDIENTS],
    )
    cur.executemany(
        # Cocktails vor Rezeptzeilen anlegen.
        "INSERT INTO cocktails (cocktail_id, cocktail_name) VALUES (?, ?)",
        [(x["cocktail_id"], x["cocktail_name"]) for x in SEED_COCKTAILS],
    )
    cur.executemany(
        """
        INSERT INTO cocktail_ingredients (cocktail_id, ingredient_id, amount_ml, order_index)
        VALUES (?, ?, ?, ?)
        """,
        [
            (x["cocktail_id"], x["ingredient_id"], x["amount_ml"], x["order_index"])
            for x in SEED_COCKTAIL_INGREDIENTS
        ],
    )
    cur.executemany(
        # Pumpen bekommen Startwerte fuer Zuordnung und Kalibrierung.
        """
        INSERT INTO pumps (pump_id, pump_number, ingredient_id, flow_rate_ml_s, position_steps)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (x["pump_id"], x["pump_number"], x["ingredient_id"], x["flow_rate_ml_s"], x["position_steps"])
            for x in SEED_PUMPS
        ],
    )
    cur.executemany(
        # Regalebenen fuer die Adminansicht vorbelegen.
        "INSERT INTO levels (levelnumber) VALUES (?)",
        [(x["levelnumber"],) for x in SEED_LEVELS],
    )
    cur.executemany(
        # Maschinenparameter liefern sinnvolle Startpositionen.
        "INSERT INTO machine_parameters (param_key, param_value) VALUES (?, ?)",
        [(x["param_key"], x["param_value"]) for x in SEED_MACHINE_PARAMETERS],
    )
