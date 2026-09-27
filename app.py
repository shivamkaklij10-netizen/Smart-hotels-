from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "smart-hotel-2026"
DB = "hotel.db"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,role TEXT DEFAULT 'user');
    CREATE TABLE IF NOT EXISTS bookings(
      id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,
      type TEXT,name TEXT,date TEXT,time TEXT,details TEXT,
      status TEXT DEFAULT 'Pending');
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,
      item TEXT,quantity INTEGER,total REAL,
      status TEXT DEFAULT 'Pending');
    """)
    if not c.execute(
        "SELECT id FROM users WHERE email=?", ("admin@smarthotel.com",)
    ).fetchone():
        c.execute(
            "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (
                "Hotel Admin",
                "admin@smarthotel.com",
                generate_password_hash("admin123"),
                "admin",
            ),
        )
    c.commit()
    c.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        c = db()
        try:
            c.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, generate_password_hash(password)),
            )
            c.commit()
            c.close()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            c.close()
            flash("Email already registered.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        c = db()
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        c.close()
        if u and check_password_hash(u["password"], password):
            session.update(user_id=u["id"], name=u["name"], role=u["role"])
            return redirect(
                url_for("admin") if u["role"] == "admin" else url_for("dashboard")
            )
        flash("Invalid email or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/menu")
def menu():
    return render_template("menu.html")


@app.route("/order", methods=["POST"])
def order():
    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))
    item = request.form["item"]
    qty = int(request.form["quantity"])
    price = float(request.form["price"])
    c = db()
    c.execute(
        "INSERT INTO orders(user_id,item,quantity,total) VALUES(?,?,?,?)",
        (session["user_id"], item, qty, price * qty),
    )
    c.commit()
    c.close()
    flash("Food order placed successfully.")
    return redirect(url_for("dashboard"))


@app.route("/booking", methods=["GET", "POST"])
def booking():
    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))
    if request.method == "POST":
        c = db()
        c.execute(
            """INSERT INTO bookings(user_id,type,name,date,time,details)
          VALUES(?,?,?,?,?,?)""",
            (
                session["user_id"],
                request.form["type"],
                request.form["name"],
                request.form["date"],
                request.form.get("time", ""),
                request.form.get("details", ""),
            ),
        )
        c.commit()
        c.close()
        flash("Booking submitted successfully.")
        return redirect(url_for("dashboard"))
    return render_template("booking.html")


@app.route("/rooms")
def rooms():
    return render_template("rooms.html")


@app.route("/party")
def party():
    return render_template("party.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    c = db()
    bookings = c.execute(
        "SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    orders = c.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    c.close()
    return render_template("dashboard.html", bookings=bookings, orders=orders)


@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    c = db()
    users = c.execute(
        "SELECT id,name,email,role FROM users ORDER BY id DESC"
    ).fetchall()
    bookings = c.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    orders = c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    c.close()
    return render_template("admin.html", users=users, bookings=bookings, orders=orders)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
