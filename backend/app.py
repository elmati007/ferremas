from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.secret_key = os.urandom(24)  # Genera una clave secreta para manejar las sesiones
app.config['UPLOAD_FOLDER'] = os.path.join('backend', 'static', 'img')  # Carpeta para almacenar imágenes subidas
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # Extensiones permitidas para imágenes

# Función para verificar que el archivo sea de tipo imagen
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Ruta principal - Página del cliente
@app.route('/')
def home():
    conn = sqlite3.connect('backend/database.db')
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, descripcion, precio, imagen FROM productos")
    productos = cursor.fetchall()
    conn.close()
    return render_template('home.html', productos=productos)

# Ruta del administrador
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        imagen = request.files['imagen']

        if imagen and allowed_file(imagen.filename):
            imagen_filename = os.urandom(24).hex() + os.path.splitext(imagen.filename)[1]
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename))
        else:
            imagen_filename = None

        conn = sqlite3.connect('backend/database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (nombre, descripcion, precio, imagen) VALUES (?, ?, ?, ?)",
                       (nombre, descripcion, precio, imagen_filename))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    conn = sqlite3.connect('backend/database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, descripcion, precio, imagen FROM productos")
    productos = cursor.fetchall()
    conn.close()
    return render_template('admin.html', productos=productos)

# Eliminar producto
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    conn = sqlite3.connect('backend/database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM productos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

# Agregar producto al carrito (AJAX-compatible)
@app.route('/agregar-al-carrito/<int:id>', methods=['POST'])
def agregar_al_carrito(id):
    conn = sqlite3.connect('backend/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, descripcion, precio, imagen FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404

    if 'carrito' not in session:
        session['carrito'] = []

    session['carrito'].append({
        'nombre': producto[0],
        'descripcion': producto[1],
        'precio': producto[2],
        'imagen': producto[3]
    })

    session.modified = True
    return jsonify({'message': 'Producto agregado al carrito'}), 200

# Ver carrito
@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    total = sum(item['precio'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)

# Eliminar producto del carrito
@app.route('/eliminar_del_carrito/<int:index>', methods=['POST'])
def eliminar_del_carrito(index):
    carrito = session.get('carrito', [])
    if len(carrito) > index:
        del carrito[index]
    session.modified = True
    return redirect(url_for('carrito'))

if __name__ == '__main__':
    app.run(debug=True)
