-- Fremdschlüssel aktivieren
PRAGMA foreign_keys = ON;

-- Users
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

-- Ingredients
CREATE TABLE IF NOT EXISTS Ingredients (
    ingredient_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    quantity_available REAL
);

-- 1) Ebenen (Levels)
CREATE TABLE IF NOT EXISTS Levels (
    level_id INTEGER PRIMARY KEY,
    level_number INTEGER NOT NULL UNIQUE,                 -- 1,2,3 ...
    name TEXT,                                            -- z.B. '1. Ebene'
    z_height_mm REAL                                      -- optionale physische Z-Höhe
);

-- 2) Förderband-/Mixerübergabe-Konfigurationen
CREATE TABLE IF NOT EXISTS Conveyor_Handover_Configs (
    config_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,                            -- z.B. 'Standard'
    height_mm REAL NOT NULL,                              -- Mixerhöhe (Z)
    distance_mm REAL NOT NULL,                            -- Förderbanddistanz
    direction TEXT NOT NULL CHECK (direction IN ('forward','backward','left','right')),
    speed_mm_s REAL,                                      -- optional
    notes TEXT
);

-- Cocktails (mit Verknüpfung zur Ebene und optional einer Übergabekonfiguration)
CREATE TABLE IF NOT EXISTS Cocktails (
    cocktail_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    level_id INTEGER,                                     -- Ebene
    handover_config_id INTEGER,                           -- optional: Standard-Übergabeprofil
    FOREIGN KEY (level_id) REFERENCES Levels(level_id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (handover_config_id) REFERENCES Conveyor_Handover_Configs(config_id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Cocktail_Ingredients
CREATE TABLE IF NOT EXISTS Cocktail_Ingredients (
    id INTEGER PRIMARY KEY,
    cocktail_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity_required REAL,
    FOREIGN KEY (cocktail_id) REFERENCES Cocktails(cocktail_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Orders
CREATE TABLE IF NOT EXISTS Orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    cocktail_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','in_progress','completed')),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (cocktail_id) REFERENCES Cocktails(cocktail_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Order_Queue
CREATE TABLE IF NOT EXISTS Order_Queue (
    queue_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    position_in_queue INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 3) Pumps (physische Pumpen 1..5, Zuordnung zu einer Zutat)
CREATE TABLE IF NOT EXISTS Pumps (
    pump_id INTEGER PRIMARY KEY,
    pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 5),  -- 1..5
    name TEXT,
    ingredient_id INTEGER,                               -- aktuell bestückte Zutat
    gpio_pin INTEGER,                                    -- z.B. Relais/GPIO
    flow_rate_ml_s REAL,                                 -- Kalibrierung (ml/s)
    priming_time_s REAL,                                 -- Vorlaufzeit
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE SET NULL ON UPDATE CASCADE
);
