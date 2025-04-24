from flask import Flask, request, render_template
from datetime import datetime
import numpy as np
import tensorflow as tf
from PIL import Image
import cv2
import mediapipe as mp
from tensorflow.keras.applications.mobilenet import preprocess_input
from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file

app = Flask(__name__)

modelo = tf.keras.models.load_model("emotion_face_mobilNet.h5")
emociones = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
app.secret_key = "clave_secreta_segura_123"  # Cambia esto en producción

@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect('/login')  
    return render_template('index.html')




@app.route('/predecir', methods=['POST'])
def predecir():
    imagen = request.files['imagen']
    nombre = request.form.get('nombre')
    edad = request.form.get('edad')

    if not imagen:
        return render_template('index.html', error="❌ No se envió ninguna imagen.")

    # Preprocesamiento
    img = Image.open(imagen).convert('RGB').resize((224, 224))
    img_array = np.array(img) / 255.0
    img_array = img_array.reshape(1, 224, 224, 3)

    # medir tiempo de Predicción
    start = time.time()
    pred = modelo.predict(img_array)
    end = time.time()
    tiempo_procesamiento = round(end - start, 2)

    # Interpretar resultado
    emocion_idx = np.argmax(pred)
    emocion = emociones[emocion_idx]
    confianza = float(pred[0][emocion_idx]) * 100

    # Guardar imagen
    now = datetime.now()
    filename = f"{nombre.replace(' ', '_')}_{now.strftime('%Y%m%d%H%M%S')}.jpg"
    imagen_path = f"static/fotos/{filename}"
    img.save(imagen_path)

    # Enviar datos al modal (render_template activa el HTML)
    return render_template('index.html',
                           emocion=emocion,
                           confianza=f"{confianza:.2f}%",
                           imagen_guardada=filename,
                           nombre=nombre,
                           edad=edad,
                           tiempo=tiempo_procesamiento)



@app.route("/historial")
def historial():
    if 'usuario_id' not in session:
        return redirect('/login')

    nombre = request.args.get('nombre', '').strip()
    emocion = request.args.get('emocion', '').strip().lower()
    fecha = request.args.get('fecha', '').strip()

    query = '''
    SELECT nombre, edad, fecha, hora, emocion, imagen_path, tiempo_procesamiento
    FROM registros
    WHERE usuario_id = ?
    '''
    params = [session['usuario_id']]

    if nombre:
        query += " AND nombre LIKE ?"
        params.append(f"%{nombre}%")
    if emocion:
        query += " AND lower(emocion) = ?"
        params.append(emocion)
    if fecha:
        query += " AND fecha = ?"
        params.append(fecha)

    # Solo agregamos el ORDER BY una vez al final
    query += " ORDER BY fecha DESC, hora DESC"

    conn = sqlite3.connect('data/emociones.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    datos = cursor.fetchall()
    conn.close()

    historial_data = []
    for idx, fila in enumerate(datos, 1):
        historial_data.append({
            "no": idx,
            "nombre": fila[0],
            "edad": fila[1],
            "fecha": f"{fila[2]} {fila[3]}",
            "emocion": fila[4].capitalize(),
            "foto": fila[5],
            "tiempo": f"{fila[6]:.2f}" if fila[6] else "-"
        })

    return render_template("historial.html", historial=historial_data)


# INICIAR SESION
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('usuario')
        password = request.form.get('password')

        conn = sqlite3.connect('data/emociones.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['usuario_id'] = user[0]
            session['email'] = email
            return redirect('/')
        else:
            return render_template("login.html", error="Credenciales inválidas.")

    return render_template("login.html")


# CREAR CUENTA
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return render_template("register.html", error="Todos los campos son obligatorios.")

        conn = sqlite3.connect('data/emociones.db')
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template("register.html", error="El correo ya está registrado.")

        hash_password = generate_password_hash(password)

        cursor.execute("INSERT INTO usuarios (email, password) VALUES (?, ?)", (email, hash_password))
        conn.commit()
        conn.close()

        return render_template("register.html", success="Cuenta creada correctamente ✅")

    return render_template("register.html")


#PROTEGER RUTAS ANTES DE LAS VISTAS
@app.before_request
def requerir_login():
    rutas_protegidas = ['index', 'predecir', 'historial']
    if request.endpoint in rutas_protegidas and 'usuario_id' not in session:
        return redirect('/login')

#CERRAR SESiÓN
@app.route('/logout')
def logout():
    session.clear() 
    return redirect('/login')

#guardar datos en la BD (emociones)
@app.route('/guardar', methods=['POST'])
def guardar():
    nombre = request.form.get('nombre')
    edad = request.form.get('edad')
    emocion = request.form.get('emocion')
    confianza = request.form.get('confianza')
    imagen_path = request.form.get('imagen_path')
    tiempo = request.form.get('tiempo')

    now = datetime.now()
    fecha = now.strftime("%Y-%m-%d")
    hora = now.strftime("%H:%M:%S")
    usuario_id = session.get('usuario_id', 1)  # temporal por si no hay login

    conn = sqlite3.connect('data/emociones.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO registros (nombre, edad, fecha, hora, emocion, imagen_path, usuario_id, tiempo_procesamiento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, int(edad), fecha, hora, emocion, imagen_path, usuario_id, float(tiempo)))
    conn.commit()
    conn.close()

    return redirect("/historial")

#exportar pdf
@app.route('/exportar_pdf')
def exportar_pdf():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect('/login')

    conn = sqlite3.connect('data/emociones.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT nombre, edad, fecha, hora, emocion, tiempo_procesamiento
        FROM registros
        WHERE usuario_id = ?
        ORDER BY fecha DESC, hora DESC
    ''', (usuario_id,))
    registros = cursor.fetchall()
    conn.close()

    # Crear PDF en memoria
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "Historial de Emociones Detectadas")

    c.setFont("Helvetica", 10)
    y = height - 80
    for idx, r in enumerate(registros, 1):
        texto = f"{idx}. {r[0]} | Edad: {r[1]} | Fecha: {r[2]} {r[3]} | Emoción: {r[4]} | Tiempo: {r[5]}s"
        c.drawString(50, y, texto)
        y -= 18
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50

    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="historial_emociones.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
