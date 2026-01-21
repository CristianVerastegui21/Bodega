import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    precio REAL NOT NULL,
    stock INTEGER NOT NULL,
    stock_minimo INTEGER NOT NULL,
    activo INTEGER DEFAULT 1,
    alertado INTEGER DEFAULT 0


)
""")

conn.commit()
conn.close()

print("✅ Base de datos creada correctamente")
