from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'img')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
DB_PATH = os.path.join(app.root_path, 'database.db')

# Helpers

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('login', next=request.path))
            if session.get('role') not in roles:
                flash('No tienes permiso para acceder a esa página.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


@app.context_processor
def inject_user():
    def order_status_badge(status):
        mapping = {
            'Pendiente': 'warning',
            'Pago Pendiente': 'warning',
            'Pagado': 'success',
            'Pago Rechazado': 'danger',
            'Aprobado': 'primary',
            'Preparando': 'info',
            'Despachado': 'secondary',
            'Entregado': 'success',
            'Rechazado': 'danger'
        }
        return mapping.get(status, 'dark')

    return {
        'current_user': session.get('username'),
        'current_role': session.get('role'),
        'current_name': session.get('name'),
        'order_status_badge': order_status_badge
    }


@app.route('/')
def home():
    conn = get_db_connection()
    productos = conn.execute("SELECT id, nombre, descripcion, precio, imagen, stock FROM productos").fetchall()
    conn.close()
    return render_template('home.html', productos=productos)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not nombre or not email or not username or not password:
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('register.html')

        conn = get_db_connection()
        existing = conn.execute(
            "SELECT id FROM usuarios WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing:
            flash('El nombre de usuario o el correo ya están registrados.', 'danger')
            conn.close()
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO usuarios (nombre, email, username, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            (nombre, email, username, password_hash, 'cliente')
        )
        conn.commit()
        conn.close()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()

        if not identifier or not password:
            flash('Ingresa usuario/correo y contraseña.', 'warning')
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? OR email = ?",
            (identifier, identifier)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['nombre']
            session['role'] = user['role']

            if user['role'] == 'administrador':
                return redirect(url_for('admin'))
            if user['role'] == 'vendedor':
                return redirect(url_for('vendedor_dashboard'))
            if user['role'] == 'bodeguero':
                return redirect(url_for('bodeguero_dashboard'))
            if user['role'] == 'contador':
                return redirect(url_for('contador_dashboard'))

            return redirect(url_for('dashboard'))

        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'administrador':
        return redirect(url_for('admin'))
    if role == 'vendedor':
        return redirect(url_for('vendedor_dashboard'))
    if role == 'bodeguero':
        return redirect(url_for('bodeguero_dashboard'))
    if role == 'contador':
        return redirect(url_for('contador_dashboard'))
    return render_template('dashboard_cliente.html')


@app.route('/admin', methods=['GET', 'POST'])
@roles_required('administrador')
def admin():
    conn = get_db_connection()

    if request.method == 'POST' and 'tipo_form' in request.form:
        if request.form['tipo_form'] == 'producto':
            nombre = request.form.get('nombre', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            precio = request.form.get('precio', '').strip()
            imagen = request.files.get('imagen')
            imagen_filename = None

            if imagen and allowed_file(imagen.filename):
                imagen_filename = os.urandom(24).hex() + os.path.splitext(imagen.filename)[1]
                imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename))

            if nombre and precio:
                conn.execute(
                    "INSERT INTO productos (nombre, descripcion, precio, imagen) VALUES (?, ?, ?, ?)",
                    (nombre, descripcion, precio, imagen_filename)
                )
                conn.commit()
                flash('Producto agregado correctamente.', 'success')
            else:
                flash('Complete nombre y precio del producto.', 'warning')

        elif request.form['tipo_form'] == 'empleado':
            nombre = request.form.get('nombre_empleado', '').strip()
            email = request.form.get('email_empleado', '').strip().lower()
            username = request.form.get('username_empleado', '').strip()
            password = request.form.get('password_empleado', '').strip()
            role = request.form.get('role_empleado', 'vendedor')

            if not nombre or not email or not username or not password:
                flash('Complete todos los campos del empleado.', 'warning')
            else:
                existing = conn.execute(
                    "SELECT id FROM usuarios WHERE username = ? OR email = ?",
                    (username, email)
                ).fetchone()
                if existing:
                    flash('Ya existe un usuario con ese correo o nombre de usuario.', 'danger')
                else:
                    password_hash = generate_password_hash(password)
                    conn.execute(
                        "INSERT INTO usuarios (nombre, email, username, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                        (nombre, email, username, password_hash, role)
                    )
                    conn.commit()
                    flash('Empleado creado correctamente.', 'success')

    productos = conn.execute("SELECT id, nombre, descripcion, precio, imagen FROM productos").fetchall()
    empleados = conn.execute(
        "SELECT id, nombre, email, username, role FROM usuarios WHERE role != 'cliente'"
    ).fetchall()
    conn.close()
    return render_template('admin.html', productos=productos, empleados=empleados)


@app.route('/eliminar/<int:id>', methods=['POST'])
@roles_required('administrador')
def eliminar_producto(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM productos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Producto eliminado.', 'success')
    return redirect(url_for('admin'))


@app.route('/agregar-al-carrito/<int:id>', methods=['POST'])
def agregar_al_carrito(id):
    conn = get_db_connection()
    producto = conn.execute(
        "SELECT nombre, descripcion, precio, imagen FROM productos WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()

    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404

    if 'carrito' not in session:
        session['carrito'] = []

    session['carrito'].append({
        'id': id,
        'nombre': producto['nombre'],
        'descripcion': producto['descripcion'],
        'precio': producto['precio'],
        'imagen': producto['imagen']
    })
    session.modified = True
    return jsonify({'message': 'Producto agregado al carrito'}), 200


@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    total = sum(item['precio'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)


@app.route('/eliminar_del_carrito/<int:index>', methods=['POST'])
def eliminar_del_carrito(index):
    carrito = session.get('carrito', [])
    if 0 <= index < len(carrito):
        carrito.pop(index)
    session.modified = True
    return redirect(url_for('carrito'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    carrito = session.get('carrito', [])
    if not carrito:
        flash('No tienes productos en el carrito.', 'warning')
        return redirect(url_for('carrito'))

    total = sum(item['precio'] for item in carrito)

    if request.method == 'POST':
        metodo_pago = request.form.get('metodo_pago', 'Crédito')
        tipo_entrega = request.form.get('tipo_entrega', 'Retiro en tienda')
        direccion_envio = request.form.get('direccion_envio', '')

        if tipo_entrega == 'Despacho a domicilio' and not direccion_envio:
            flash('Debes proporcionar una dirección para despacho a domicilio.', 'warning')
            return render_template('checkout.html', carrito=carrito, total=total,
                                 metodo_pago=metodo_pago, tipo_entrega=tipo_entrega,
                                 direccion_envio=direccion_envio)

        # Validar stock disponible
        conn = get_db_connection()
        stock_valido = True
        for item in carrito:
            producto = conn.execute(
                "SELECT stock FROM productos WHERE id = ?",
                (item['id'],)
            ).fetchone()
            if not producto or producto['stock'] < 1:
                flash(f"El producto '{item['nombre']}' no tiene stock disponible.", 'danger')
                stock_valido = False
                break

        if not stock_valido:
            conn.close()
            return render_template('checkout.html', carrito=carrito, total=total,
                                 metodo_pago=metodo_pago, tipo_entrega=tipo_entrega,
                                 direccion_envio=direccion_envio)

        # Crear pedido en estado de pago pendiente
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos (usuario_id, total, metodo_pago, tipo_entrega, direccion_envio, estado) VALUES (?, ?, ?, ?, ?, 'Pago Pendiente')",
            (session['user_id'], total, metodo_pago, tipo_entrega, direccion_envio if tipo_entrega == 'Despacho a domicilio' else None)
        )
        pedido_id = cursor.lastrowid

        # Guardar detalles del pedido sin descontar stock aún
        for item in carrito:
            cursor.execute(
                "INSERT INTO detalle_pedido (pedido_id, producto_id, nombre, descripcion, precio, cantidad, subtotal, imagen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pedido_id, item['id'], item['nombre'], item['descripcion'], item['precio'], 1, item['precio'], item['imagen'])
            )

        conn.commit()
        conn.close()

        return redirect(url_for('webpay', pedido_id=pedido_id))

    return render_template('checkout.html', carrito=carrito, total=total)


@app.route('/confirmacion-pedido/<int:pedido_id>')
@login_required
def confirmacion_pedido(pedido_id):
    conn = get_db_connection()
    pedido = conn.execute(
        "SELECT p.*, u.nombre as cliente_nombre FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ? AND p.usuario_id = ?",
        (pedido_id, session['user_id'])
    ).fetchone()
    
    if not pedido:
        conn.close()
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('home'))
    
    items = conn.execute(
        "SELECT * FROM detalle_pedido WHERE pedido_id = ?",
        (pedido_id,)
    ).fetchall()
    conn.close()
    
    return render_template('confirmacion_pedido.html', pedido=pedido, items=items)


@app.route('/webpay/<int:pedido_id>', methods=['GET', 'POST'])
@login_required
def webpay(pedido_id):
    conn = get_db_connection()
    pedido = conn.execute(
        "SELECT p.*, u.nombre as cliente_nombre FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ? AND p.usuario_id = ?",
        (pedido_id, session['user_id'])
    ).fetchone()

    if not pedido:
        conn.close()
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('home'))

    items = conn.execute(
        "SELECT * FROM detalle_pedido WHERE pedido_id = ?",
        (pedido_id,)
    ).fetchall()

    if request.method == 'POST':
        accion = request.form.get('accion')
        if accion == 'aprobar':
            stock_valido = True
            for item in items:
                producto = conn.execute(
                    "SELECT stock FROM productos WHERE id = ?",
                    (item['producto_id'],)
                ).fetchone()
                if not producto or producto['stock'] < item['cantidad']:
                    flash(f"No hay suficiente stock para '{item['nombre']}' al procesar el pago.", 'danger')
                    stock_valido = False
                    break

            if not stock_valido:
                conn.close()
                return render_template('webpay.html', pedido=pedido, items=items)

            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pedidos SET estado = 'Pagado', pago_confirmado = 1, actualizado_en = CURRENT_TIMESTAMP WHERE id = ? AND estado = 'Pago Pendiente'",
                (pedido_id,)
            )
            for item in items:
                cursor.execute(
                    "UPDATE productos SET stock = stock - ? WHERE id = ?",
                    (item['cantidad'], item['producto_id'])
                )
            conn.commit()
            conn.close()
            session.pop('carrito', None)
            flash('Pago aprobado correctamente. Tu pedido fue procesado.', 'success')
            return redirect(url_for('confirmacion_pedido', pedido_id=pedido_id))

        if accion == 'rechazar':
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pedidos SET estado = 'Pago Rechazado', actualizado_en = CURRENT_TIMESTAMP WHERE id = ? AND estado = 'Pago Pendiente'",
                (pedido_id,)
            )
            conn.commit()
            conn.close()
            flash('El pago fue rechazado. El pedido se mantuvo sin cambios.', 'danger')
            return redirect(url_for('webpay', pedido_id=pedido_id))

        flash('Acción de pago inválida.', 'danger')

    conn.close()
    return render_template('webpay.html', pedido=pedido, items=items)


@app.route('/mis-pedidos')
@roles_required('cliente')
def mis_pedidos():
    conn = get_db_connection()
    pedidos = conn.execute(
        "SELECT p.id, p.estado, p.total, p.pago_confirmado, p.creado_en, p.actualizado_en FROM pedidos p WHERE p.usuario_id = ? ORDER BY p.creado_en DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('mis_pedidos.html', pedidos=pedidos)


@app.route('/pedido/<int:pedido_id>')
@login_required
def pedido_detalle(pedido_id):
    conn = get_db_connection()
    pedido = conn.execute(
        "SELECT p.*, u.nombre as cliente_nombre, u.username as cliente_usuario FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ?",
        (pedido_id,)
    ).fetchone()
    if not pedido:
        conn.close()
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('home'))

    if session.get('role') == 'cliente' and pedido['usuario_id'] != session.get('user_id'):
        conn.close()
        flash('No tienes permiso para ver este pedido.', 'danger')
        return redirect(url_for('home'))

    items = conn.execute(
        "SELECT * FROM detalle_pedido WHERE pedido_id = ?",
        (pedido_id,)
    ).fetchall()
    conn.close()
    return render_template('pedido_detalle.html', pedido=pedido, items=items)


@app.route('/pedidos-vendedor')
@roles_required('vendedor')
def pedidos_vendedor():
    conn = get_db_connection()
    pedidos = conn.execute(
        "SELECT p.id, p.estado, p.total, p.pago_confirmado, p.creado_en, u.nombre AS cliente_nombre FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id WHERE p.estado IN ('Pendiente', 'Aprobado') ORDER BY p.creado_en DESC"
    ).fetchall()
    conn.close()
    return render_template('pedidos_vendedor.html', pedidos=pedidos)


@app.route('/pedido/<int:pedido_id>/accion-vendedor', methods=['POST'])
@roles_required('vendedor')
def accion_vendedor(pedido_id):
    accion = request.form.get('accion')
    if accion not in ['aprobar', 'rechazar']:
        flash('Acción inválida.', 'danger')
        return redirect(url_for('pedidos_vendedor'))

    nuevo_estado = 'Aprobado' if accion == 'aprobar' else 'Rechazado'
    conn = get_db_connection()
    conn.execute(
        "UPDATE pedidos SET estado = ?, actualizado_en = CURRENT_TIMESTAMP WHERE id = ? AND estado = 'Pendiente'",
        (nuevo_estado, pedido_id)
    )
    conn.commit()
    conn.close()
    flash(f'Pedido {"aprobado" if accion == "aprobar" else "rechazado"} correctamente.', 'success')
    return redirect(url_for('pedidos_vendedor'))


@app.route('/pedidos-bodeguero')
@roles_required('bodeguero')
def pedidos_bodeguero():
    conn = get_db_connection()
    pedidos = conn.execute(
        "SELECT p.id, p.estado, p.total, p.pago_confirmado, p.creado_en, u.nombre AS cliente_nombre FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id WHERE p.estado IN ('Aprobado', 'Preparando') ORDER BY p.creado_en DESC"
    ).fetchall()
    conn.close()
    return render_template('pedidos_bodeguero.html', pedidos=pedidos)


@app.route('/pedido/<int:pedido_id>/accion-bodega', methods=['POST'])
@roles_required('bodeguero')
def accion_bodega(pedido_id):
    accion = request.form.get('accion')
    if accion not in ['preparar', 'despachar']:
        flash('Acción inválida.', 'danger')
        return redirect(url_for('pedidos_bodeguero'))

    nuevo_estado = 'Preparando' if accion == 'preparar' else 'Despachado'
    estado_actual = 'Aprobado' if accion == 'preparar' else 'Preparando'
    conn = get_db_connection()
    conn.execute(
        "UPDATE pedidos SET estado = ?, actualizado_en = CURRENT_TIMESTAMP WHERE id = ? AND estado = ?",
        (nuevo_estado, pedido_id, estado_actual)
    )
    conn.commit()
    conn.close()
    flash('Estado del pedido actualizado correctamente.', 'success')
    return redirect(url_for('pedidos_bodeguero'))


@app.route('/pedidos-contador')
@roles_required('contador')
def pedidos_contador():
    conn = get_db_connection()
    pedidos = conn.execute(
        "SELECT p.id, p.estado, p.total, p.pago_confirmado, p.creado_en, u.nombre AS cliente_nombre FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id WHERE p.estado = 'Aprobado' ORDER BY p.creado_en DESC"
    ).fetchall()
    conn.close()
    return render_template('pedidos_contador.html', pedidos=pedidos)


@app.route('/pedido/<int:pedido_id>/confirmar-pago', methods=['POST'])
@roles_required('contador')
def confirmar_pago(pedido_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE pedidos SET pago_confirmado = 1, actualizado_en = CURRENT_TIMESTAMP WHERE id = ? AND estado = 'Aprobado'",
        (pedido_id,)
    )
    conn.commit()
    conn.close()
    flash('Pago confirmado correctamente.', 'success')
    return redirect(url_for('pedidos_contador'))


@app.route('/admin/pedidos')
@roles_required('administrador')
def pedidos_admin():
    conn = get_db_connection()
    pedidos = conn.execute(
        "SELECT p.id, p.estado, p.total, p.pago_confirmado, p.creado_en, p.actualizado_en, u.nombre AS cliente_nombre FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id ORDER BY p.creado_en DESC"
    ).fetchall()
    conn.close()
    return render_template('pedidos_admin.html', pedidos=pedidos)


@app.route('/pedido/<int:pedido_id>/marcar-entregado', methods=['POST'])
@login_required
def marcar_entregado(pedido_id):
    conn = get_db_connection()
    pedido = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if not pedido:
        conn.close()
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('home'))

    if session.get('role') == 'cliente' and pedido['usuario_id'] != session.get('user_id'):
        conn.close()
        flash('No tienes permiso para actualizar este pedido.', 'danger')
        return redirect(url_for('home'))

    if pedido['estado'] != 'Despachado':
        conn.close()
        flash('Solo se puede marcar como entregado un pedido despachado.', 'warning')
        return redirect(url_for('pedido_detalle', pedido_id=pedido_id))

    conn.execute(
        "UPDATE pedidos SET estado = 'Entregado', actualizado_en = CURRENT_TIMESTAMP WHERE id = ?",
        (pedido_id,)
    )
    conn.commit()
    conn.close()
    flash('Pedido marcado como entregado.', 'success')
    return redirect(url_for('pedido_detalle', pedido_id=pedido_id))


@app.route('/vendedor')
@roles_required('vendedor')
def vendedor_dashboard():
    conn = get_db_connection()
    
    # Pedidos pendientes (estado = 'Pendiente')
    pedidos_pendientes = conn.execute(
        """SELECT p.id, p.estado, p.total, p.pago_confirmado, p.metodo_pago, 
                  p.tipo_entrega, p.creado_en, p.actualizado_en,
                  u.nombre AS cliente_nombre 
           FROM pedidos p 
           JOIN usuarios u ON p.usuario_id = u.id 
           WHERE p.estado = 'Pendiente' 
           ORDER BY p.creado_en DESC"""
    ).fetchall()
    
    # Pedidos aprobados hoy (estado = 'Aprobado' Y fecha de hoy)
    today = datetime.now().strftime('%Y-%m-%d')
    
    aprobados_hoy = conn.execute(
        """SELECT p.id, p.estado, p.total, p.pago_confirmado, p.metodo_pago,
                  p.tipo_entrega, p.creado_en, p.actualizado_en,
                  u.nombre AS cliente_nombre 
           FROM pedidos p 
           JOIN usuarios u ON p.usuario_id = u.id 
           WHERE p.estado = 'Aprobado' 
           AND DATE(p.actualizado_en) = ?
           ORDER BY p.actualizado_en DESC
           LIMIT 10""",
        (today,)
    ).fetchall()
    
    # Total monto pendiente
    total_pendiente_row = conn.execute(
        "SELECT SUM(total) as total FROM pedidos WHERE estado = 'Pendiente'"
    ).fetchone()
    total_pendiente = total_pendiente_row['total'] or 0
    
    # Total ingresos aprobados hoy
    total_aprobados_hoy_row = conn.execute(
        """SELECT SUM(total) as total FROM pedidos 
           WHERE estado = 'Aprobado' AND DATE(actualizado_en) = ?""",
        (today,)
    ).fetchone()
    total_aprobados_hoy = total_aprobados_hoy_row['total'] or 0
    
    conn.close()
    
    return render_template(
        'dashboard_vendedor.html',
        pedidos_pendientes=pedidos_pendientes,
        aprobados_hoy=aprobados_hoy,
        total_pendiente=total_pendiente,
        total_aprobados_hoy=total_aprobados_hoy
    )


@app.route('/bodeguero')
@roles_required('bodeguero')
def bodeguero_dashboard():
    conn = get_db_connection()
    
    # Pedidos aprobados (estado = 'Aprobado')
    pedidos_aprobados = conn.execute(
        """SELECT p.id, p.estado, p.total, p.pago_confirmado, p.metodo_pago,
                  p.tipo_entrega, p.direccion_envio, p.creado_en, p.actualizado_en,
                  u.nombre AS cliente_nombre 
           FROM pedidos p 
           JOIN usuarios u ON p.usuario_id = u.id 
           WHERE p.estado = 'Aprobado' 
           ORDER BY p.creado_en ASC"""
    ).fetchall()
    
    # Pedidos en preparación (estado = 'Preparando')
    pedidos_preparando = conn.execute(
        """SELECT p.id, p.estado, p.total, p.pago_confirmado, p.metodo_pago,
                  p.tipo_entrega, p.direccion_envio, p.creado_en, p.actualizado_en,
                  u.nombre AS cliente_nombre 
           FROM pedidos p 
           JOIN usuarios u ON p.usuario_id = u.id 
           WHERE p.estado = 'Preparando' 
           ORDER BY p.actualizado_en ASC"""
    ).fetchall()
    
    # Total de productos en el sistema
    total_productos = conn.execute(
        "SELECT COUNT(*) as count FROM productos"
    ).fetchone()['count']
    
    # Productos con stock bajo (menos de 10 unidades)
    productos_stock_bajo = conn.execute(
        """SELECT id, nombre, precio, stock 
           FROM productos 
           WHERE stock < 10 
           ORDER BY stock ASC"""
    ).fetchall()
    
    conn.close()
    
    return render_template(
        'dashboard_bodeguero.html',
        pedidos_aprobados=pedidos_aprobados,
        pedidos_preparando=pedidos_preparando,
        total_productos=total_productos,
        productos_stock_bajo=productos_stock_bajo
    )


@app.route('/contador')
@roles_required('contador')
def contador_dashboard():
    conn = get_db_connection()
    
    # Pedidos aprobados pendientes de pago
    pedidos_pendientes = conn.execute(
        """SELECT p.id, p.estado, p.total, p.pago_confirmado, p.metodo_pago,
                  p.creado_en, p.actualizado_en,
                  u.nombre AS cliente_nombre 
           FROM pedidos p 
           JOIN usuarios u ON p.usuario_id = u.id 
           WHERE p.estado = 'Aprobado' AND p.pago_confirmado = 0
           ORDER BY p.creado_en DESC"""
    ).fetchall()
    
    # Pagos confirmados hoy
    today = datetime.now().strftime('%Y-%m-%d')
    
    pedidos_pagados_hoy = conn.execute(
        """SELECT p.id, p.estado, p.total, p.pago_confirmado, p.metodo_pago,
                  p.creado_en, p.actualizado_en,
                  u.nombre AS cliente_nombre 
           FROM pedidos p 
           JOIN usuarios u ON p.usuario_id = u.id 
           WHERE p.pago_confirmado = 1 AND DATE(p.actualizado_en) = ?
           ORDER BY p.actualizado_en DESC""",
        (today,)
    ).fetchall()
    
    # Total ingresos (pedidos con pago confirmado)
    total_ingresos_row = conn.execute(
        """SELECT SUM(total) as total FROM pedidos 
           WHERE pago_confirmado = 1"""
    ).fetchone()
    total_ingresos = total_ingresos_row['total'] or 0
    
    # Pagos pendientes (aprobados sin pagar)
    pagos_pendientes_row = conn.execute(
        """SELECT SUM(total) as total FROM pedidos 
           WHERE estado = 'Aprobado' AND pago_confirmado = 0"""
    ).fetchone()
    pagos_pendientes = pagos_pendientes_row['total'] or 0
    
    # Ingresos hoy
    ingresos_hoy_row = conn.execute(
        """SELECT SUM(total) as total FROM pedidos 
           WHERE pago_confirmado = 1 AND DATE(actualizado_en) = ?""",
        (today,)
    ).fetchone()
    ingresos_hoy = ingresos_hoy_row['total'] or 0
    
    conn.close()
    
    return render_template(
        'dashboard_contador.html',
        pedidos_pendientes=pedidos_pendientes,
        pedidos_pagados_hoy=pedidos_pagados_hoy,
        total_ingresos=total_ingresos,
        pagos_pendientes=pagos_pendientes,
        ingresos_hoy=ingresos_hoy
    )


if __name__ == '__main__':
    app.run(debug=True)
