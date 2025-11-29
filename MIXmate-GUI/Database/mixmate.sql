PRAGMA foreign_keys = ON;

-------------------------------------------------------
-- 1) Ingredients (Zutaten)
-------------------------------------------------------
DROP TABLE IF EXISTS ingredients;

CREATE TABLE ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Seed ingredients
INSERT INTO ingredients (name) VALUES
('Rum'),
('Cola'),
('Weisswein'),
('Holundersirup'),
('Limettensaft'),
('Tonic'),
('Gin');

-------------------------------------------------------
-- 2) Pumps (Pumpenzuordnung)
-------------------------------------------------------
DROP TABLE IF EXISTS pumps;

CREATE TABLE pumps (
    pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 6),
    ingredient_id INTEGER,                 -- Zutat in dieser Pumpe
    flow_rate_ml_s REAL NOT NULL,          -- ml pro Sekunde
    position_steps INTEGER NOT NULL,       -- Schlittenposition in Steps

    FOREIGN KEY (ingredient_id)
        REFERENCES ingredients(ingredient_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- Seed pumps (flow_rate & positions: Beispielwerte)
INSERT INTO pumps (pump_number, ingredient_id, flow_rate_ml_s, position_steps) VALUES
(1, 1, 10.0, 100),      -- Rum
(2, 2, 12.0, 300),      -- Cola
(3, 3, 11.5, 500),      -- Weisswein
(4, 4,  8.0, 700),      -- Holundersirup
(5, 5,  5.0, 900),      -- Limettensaft
(6, 6, 13.0, 1100);     -- Tonic

-------------------------------------------------------
-- 3) Cocktails (nur Name)
-------------------------------------------------------
DROP TABLE IF EXISTS cocktails;

CREATE TABLE cocktails (
    cocktail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_name TEXT NOT NULL UNIQUE
);

-- Seed cocktails
INSERT INTO cocktails (cocktail_name) VALUES
('RumCola'),
('Hugo'),
('GinTonic');

-------------------------------------------------------
-- 4) Cocktail Zutaten (Many-To-Many)
-------------------------------------------------------
DROP TABLE IF EXISTS cocktail_ingredients;

CREATE TABLE cocktail_ingredients (
    cocktail_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    amount_ml INTEGER NOT NULL,
    order_index INTEGER NOT NULL,

    PRIMARY KEY (cocktail_id, ingredient_id),

    FOREIGN KEY (cocktail_id)
        REFERENCES cocktails(cocktail_id)
        ON DELETE CASCADE,

    FOREIGN KEY (ingredient_id)
        REFERENCES ingredients(ingredient_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- Seed RumCola (cocktail_id = 1)
INSERT INTO cocktail_ingredients (cocktail_id, ingredient_id, amount_ml, order_index) VALUES
(1, 1,  50, 1),   -- Rum
(1, 2, 150, 2);   -- Cola

-- Seed Hugo (cocktail_id = 2)
INSERT INTO cocktail_ingredients (cocktail_id, ingredient_id, amount_ml, order_index) VALUES
(2, 3,  80, 1),   -- Weisswein
(2, 4,  20, 2),   -- Holundersirup
(2, 5,  10, 3);   -- Limettensaft

-- Seed GinTonic (cocktail_id = 3)
INSERT INTO cocktail_ingredients (cocktail_id, ingredient_id, amount_ml, order_index) VALUES
(3, 7,  40, 1),   -- Gin
(3, 6, 120, 2);   -- Tonic

-------------------------------------------------------
-- Optional: Indexe (bessere Performance)
-------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ci_cocktail
    ON cocktail_ingredients (cocktail_id);

CREATE INDEX IF NOT EXISTS idx_ci_order
    ON cocktail_ingredients (order_index);
