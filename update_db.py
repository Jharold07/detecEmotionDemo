import sqlite3

conn = sqlite3.connect('data/emociones.db')
cursor = conn.cursor()

# Agrega la nueva columna
cursor.execute("ALTER TABLE registros ADD COLUMN tiempo_procesamiento REAL;")

conn.commit()
conn.close()

print("Columna 'tiempo_procesamiento' agregada exitosamente ✅")
