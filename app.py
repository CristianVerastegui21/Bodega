import os
import sqlite3
import requests
import json

from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    session
)


app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
    return sqlite3.connect("bodega.db")


N8N_WEBHOOK_URL = "http://localhost:5678/webhook/alerta"

def verificar_stock1():
    conn = get_db()
    productos = conn.execute("""
        SELECT * FROM productos
        WHERE stock <= stock_minimo AND alertado = 0
    """).fetchall()

    for p in productos:
        payload = {
            "producto": p["nombre"],
            "stock": p["stock"],
            "stock_minimo": p["stock_minimo"]
        }

        try:
            requests.post(N8N_WEBHOOK_URL, json=payload, timeout=3)

            conn.execute("""
                UPDATE productos SET alertado = 1 WHERE id = ?
            """, (p["id"],))
            conn.commit()
    


        except:
            pass

    conn.close()

def verificar_stock():
    conn = get_db()

    productos = conn.execute("""
        SELECT id, nombre, stock, stock_minimo
        FROM productos
        WHERE stock <= stock_minimo AND alertado = 1
    """).fetchall()

    # Si no hay productos con stock bajo, no enviar nada
    if not productos:
        conn.close()
        return

    alerta = []
    ids = []

    for p in productos:
        alerta.append({
            "codigo": p["id"],
            "descripcion": p["nombre"],
            "stock": p["stock"],
            "reorden": p["stock_minimo"]
        })
        ids.append(p["id"])

    try:
        requests.post(
            "http://localhost:5678/webhook/alerta",
            json=alerta,
            timeout=5
        )

        # Marcar SOLO los alertados
        conn.executemany(
            "UPDATE productos SET alertado = 1 WHERE id = ?",
            [(i,) for i in ids]
        )
        conn.commit()

    except Exception as e:
        print("❌ Error enviando alerta:", e)

    conn.close()

def init_db():
    conn = get_db()
    conn.execute("""
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


# 🔥 ESTO ES LO CLAVE
with app.app_context():
    init_db()


@app.route("/")
def home():
    return jsonify({"status": "API de Bodega funcionando"})

@app.route("/web")
def web_publica():
    conn = get_db()
    productos = conn.execute("""
        SELECT nombre, categoria, precio
        FROM productos
        WHERE activo = 1 AND stock > 0
    """).fetchall()
    conn.close()

    return render_template("index.html", productos=productos)



app.secret_key = "bodega_secreta"

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["password"] == "1234":
            session["admin"] = True
            return redirect("/admin/dashboard")
        return render_template("admin_login.html", error="Credenciales incorrectas")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()
    productos = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()

    return render_template("admin_dashboard.html", productos=productos)


@app.route("/admin/producto/nuevo", methods=["GET", "POST"])
def nuevo_producto ():
    if not session.get("admin"):
        return redirect("/admin")
    

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        stock_minimo = request.form["stock_minimo"]

        conn = get_db()

        conn.execute("""
            INSERT INTO productos
            (nombre, categoria, precio, stock, stock_minimo, activo, alertado)
            VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (nombre, categoria, precio, stock, stock_minimo))

        conn.commit()
        conn.close()

        verificar_stock()
        


        return redirect("/admin/dashboard")

    return render_template("admin_producto_form.html")


@app.route("/admin/producto/editar/<int:id>", methods=["GET", "POST"])
def editar_producto(id):
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        precio = request.form["precio"]
        stock = int(request.form["stock"])
        stock_minimo = int(request.form["stock_minimo"])

        # Actualizar producto
        conn.execute("""
            UPDATE productos
            SET nombre = ?, categoria = ?, precio = ?, stock = ?, stock_minimo = ?
            WHERE id = ?
        """, (nombre, categoria, precio, stock, stock_minimo, id))

        # 🔁 LÓGICA CLAVE DE ALERTA
        if stock > stock_minimo:
            # Ya NO está en bajo stock → resetear alerta
            conn.execute("""
                UPDATE productos SET alertado = 1 WHERE id = ?
            """, (id,))

        conn.commit()
        conn.close()

        # 🔔 Verificar TODOS los productos (lista completa)
        verificar_stock()

        return redirect("/admin/dashboard")

    producto = conn.execute(
        "SELECT * FROM productos WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    return render_template(
        "admin_producto_form.html",
        producto=producto,
        editar=True
    )


@app.route("/admin/producto/eliminar/<int:id>")
def eliminar_producto(id):
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/dashboard")



@app.route("/tienda")
def tienda():
    conn = get_db()
    productos = conn.execute("""
        SELECT nombre, categoria, precio
        FROM productos
        WHERE activo = 1 AND stock > 0
        ORDER BY categoria, nombre
    """).fetchall()
    conn.close()

    return render_template("tienda.html", productos=productos)


   #if __name__ == "__main__":
   #app.run(debug=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
