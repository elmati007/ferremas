import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Crear tabla productos
cursor.execute('''
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL,
    descripcion TEXT,
    imagen TEXT,
    stock INTEGER NOT NULL DEFAULT 100
)
''')

# Crear tabla usuarios con roles
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Crear tabla pedidos
cursor.execute('''
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    total REAL NOT NULL,
    pago_confirmado INTEGER NOT NULL DEFAULT 0,
    metodo_pago TEXT NOT NULL DEFAULT 'Crédito',
    tipo_entrega TEXT NOT NULL DEFAULT 'Retiro en tienda',
    direccion_envio TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

# Crear tabla detalle_pedido
cursor.execute('''
CREATE TABLE IF NOT EXISTS detalle_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    producto_id INTEGER,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    precio REAL NOT NULL,
    cantidad INTEGER NOT NULL,
    subtotal REAL NOT NULL,
    imagen TEXT,
    FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
    FOREIGN KEY(producto_id) REFERENCES productos(id)
)
''')

# Insertar productos de ejemplo (ajusta según tus imágenes en static/img)
productos = [
    ('Taladro Bosch', 59990, 'Potente taladro con diseño ergonómico.', 'taladro_bosch.jpg', 15),
    ('Martillo Stanley', 12990, 'Ideal para trabajos de carpintería.', 'martillo_stanley.jpg', 50),
    ('Caja de Tornillos', 7990, 'Set completo de tornillos variados.', 'caja_tornillos.jpg', 100)
]
for producto in productos:
    cursor.execute('INSERT INTO productos (nombre, precio, descripcion, imagen, stock) VALUES (?, ?, ?, ?, ?)', producto)

# Insertar usuarios de prueba
usuarios = [
    ('Administrador', 'admin@ferremas.com', 'admin', generate_password_hash('Admin123!'), 'administrador'),
    ('Vendedor Ejemplo', 'vendedor@ferremas.com', 'vendedor', generate_password_hash('Vendedor123!'), 'vendedor'),
    ('Bodeguero Ejemplo', 'bodeguero@ferremas.com', 'bodeguero', generate_password_hash('Bodega123!'), 'bodeguero'),
    ('Contador Ejemplo', 'contador@ferremas.com', 'contador', generate_password_hash('Contador123!'), 'contador'),
    ('Cliente Ejemplo', 'cliente@ferremas.com', 'cliente', generate_password_hash('Cliente123!'), 'cliente')
]
for usuario in usuarios:
    cursor.execute('INSERT OR IGNORE INTO usuarios (nombre, email, username, password_hash, role) VALUES (?, ?, ?, ?, ?)', usuario)

conn.commit()
conn.close()
