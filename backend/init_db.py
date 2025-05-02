import sqlite3

# Crear conexión a database.db
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Crear tabla productos
cursor.execute('''
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL,
    descripcion TEXT,
    imagen TEXT
)
''')

# Insertar productos (ajusta los nombres de imagen según los que tengas en static/img)
cursor.execute("INSERT INTO productos (nombre, precio, descripcion, imagen) VALUES (?, ?, ?, ?)",
               ('Taladro Bosch', 59990, 'Potente taladro con diseño ergonómico.', 'taladro_bosch.jpg'))

cursor.execute("INSERT INTO productos (nombre, precio, descripcion, imagen) VALUES (?, ?, ?, ?)",
               ('Martillo Stanley', 12990, 'Ideal para trabajos de carpintería.', 'martillo_stanley.jpg'))

cursor.execute("INSERT INTO productos (nombre, precio, descripcion, imagen) VALUES (?, ?, ?, ?)",
               ('Caja de Tornillos', 7990, 'Set completo de tornillos variados.', 'caja_tornillos.jpg'))

conn.commit()
conn.close()
