import sqlite3

class PumpModel:
    def __init__(self, db_path='mixmate.db'):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pumps (
                pump_id INTEGER PRIMARY KEY,
                pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 10),
                name TEXT,
                ingredient_id INTEGER,
                flow_rate_ml_s REAL,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id)
                    ON DELETE SET NULL ON UPDATE CASCADE
            )
        ''')
        self.connection.commit()

    def add_pump(self, pump_number, name=None, ingredient_id=None, flow_rate_ml_s=None, is_active=1):
        self.cursor.execute('''
            INSERT INTO pumps (pump_number, name, ingredient_id, flow_rate_ml_s, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (pump_number, name, ingredient_id, flow_rate_ml_s, is_active))
        self.connection.commit()

    def get_pump(self, pump_id):
        self.cursor.execute('SELECT * FROM pumps WHERE pump_id = ?', (pump_id,))
        return self.cursor.fetchone()

    def update_pump(self, pump_id, pump_number=None, name=None,
                    ingredient_id=None, flow_rate_ml_s=None, is_active=None):

        updates = []
        params = []

        if pump_number is not None:
            updates.append("pump_number = ?")
            params.append(pump_number)

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if ingredient_id is not None:
            updates.append("ingredient_id = ?")
            params.append(ingredient_id)

        if flow_rate_ml_s is not None:
            updates.append("flow_rate_ml_s = ?")
            params.append(flow_rate_ml_s)

        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if not updates:
            return  # nichts zu aktualisieren

        params.append(pump_id)

        self.cursor.execute(f'''
            UPDATE pumps
            SET {", ".join(updates)}
            WHERE pump_id = ?
        ''', params)
        self.connection.commit()

    def delete_pump(self, pump_id):
        self.cursor.execute('DELETE FROM pumps WHERE pump_id = ?', (pump_id,))
        self.connection.commit()

    def list_pumps(self):
        self.cursor.execute('SELECT * FROM pumps')
        return self.cursor.fetchall()

    def __del__(self):
        self.connection.close()
