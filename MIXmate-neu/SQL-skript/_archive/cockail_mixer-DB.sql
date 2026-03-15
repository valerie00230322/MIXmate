-- Erstelle die Datenbank
CREATE DATABASE IF NOT EXISTS cocktail_mixer;
USE cocktail_mixer;
-- Tabelle: Users
CREATE TABLE Users (
user_id INT NOT NULL AUTO_INCREMENT,
username VARCHAR(50) NOT NULL,
email VARCHAR(100) NOT NULL,
password VARCHAR(255) NOT NULL,
PRIMARY KEY (user_id),
UNIQUE (username),
UNIQUE (email)
) ENGINE = InnoDB;
-- Tabelle: Ingredients
CREATE TABLE Ingredients (
ingredient_id INT NOT NULL AUTO_INCREMENT,
name VARCHAR(100) NOT NULL,
quantity_available DECIMAL(10,2),
PRIMARY KEY (ingredient_id),
UNIQUE (name)
) ENGINE = InnoDB;
-- Tabelle: Cocktails
CREATE TABLE Cocktails (
cocktail_id INT NOT NULL AUTO_INCREMENT,
name VARCHAR(100) NOT NULL,
description TEXT,
PRIMARY KEY (cocktail_id),
UNIQUE (name)
) ENGINE = InnoDB;
-- Tabelle: Cocktail_Ingredients
CREATE TABLE Cocktail_Ingredients (
id INT NOT NULL AUTO_INCREMENT,
cocktail_id INT NOT NULL,
ingredient_id INT NOT NULL,
quantity_required DECIMAL(10,2),
PRIMARY KEY (id),
FOREIGN KEY (cocktail_id) REFERENCES Cocktails(cocktail_id) ON DELETE CASCADE,
FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE CASCADE
) ENGINE = InnoDB;
-- Tabelle: Orders
CREATE TABLE Orders (
order_id INT NOT NULL AUTO_INCREMENT,
user_id INT NOT NULL,
cocktail_id INT NOT NULL,
status ENUM('pending', 'in_progress', 'completed') NOT NULL,
PRIMARY KEY (order_id),
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
FOREIGN KEY (cocktail_id) REFERENCES Cocktails(cocktail_id) ON DELETE CASCADE
) ENGINE = InnoDB;
-- Tabelle: Order_Queue
CREATE TABLE Order_Queue (
    queue_id INT NOT NULL AUTO_INCREMENT,
    order_id INT NOT NULL,
    position_in_queue INT NOT NULL,
    PRIMARY KEY (queue_id),
    FOREIGN KEY (order_id)
        REFERENCES Orders (order_id)
        ON DELETE CASCADE
)  ENGINE=INNODB;




