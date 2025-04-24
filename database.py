import sqlite3

# Crear conexión
conn = sqlite3.connect('data/emociones.db')
cursor = conn.cursor()

# Crear tabla de usuarios
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
''')

# Crear tabla de registros de emociones
cursor.execute('''
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    edad INTEGER,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    emocion TEXT NOT NULL,
    imagen_path TEXT NOT NULL,
    usuario_id INTEGER NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
''')

conn.commit()
conn.close()

print("Base de datos creada exitosamente ✅")
