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
    if not db_path:
        raise ValueError("db_path darf nicht leer sein")

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingredients (
                ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cocktails (
                cocktail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cocktail_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cocktail_ingredients (
                cocktail_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                amount_ml REAL NOT NULL CHECK (amount_ml > 0),
                order_index INTEGER NOT NULL CHECK (order_index >= 1),
                PRIMARY KEY (cocktail_id, ingredient_id),
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

            CREATE TABLE IF NOT EXISTS pumps (
                pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 10),
                ingredient_id INTEGER,
                flow_rate_ml_s REAL NOT NULL CHECK (flow_rate_ml_s > 0),
                position_steps INTEGER NOT NULL CHECK (position_steps >= 0),
                FOREIGN KEY (ingredient_id)
                    REFERENCES ingredients(ingredient_id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS levels (
                levelnumber INTEGER PRIMARY KEY,
                extension_distance REAL NOT NULL DEFAULT 0 CHECK (extension_distance >= 0)
            );

            CREATE TABLE IF NOT EXISTS machine_parameters (
                param_key TEXT PRIMARY KEY,
                param_value REAL NOT NULL
            );
            """
        )
        _seed_database_if_empty(con)
        con.commit()
    finally:
        con.close()


def _seed_database_if_empty(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM ingredients")
    ingredients_count = int(cur.fetchone()[0])
    if ingredients_count > 0:
        return

    cur.executemany(
        "INSERT INTO ingredients (ingredient_id, name) VALUES (?, ?)",
        [(x["ingredient_id"], x["name"]) for x in SEED_INGREDIENTS],
    )
    cur.executemany(
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
        "INSERT INTO levels (levelnumber, extension_distance) VALUES (?, ?)",
        [(x["levelnumber"], x["extension_distance"]) for x in SEED_LEVELS],
    )
    cur.executemany(
        "INSERT INTO machine_parameters (param_key, param_value) VALUES (?, ?)",
        [(x["param_key"], x["param_value"]) for x in SEED_MACHINE_PARAMETERS],
    )
