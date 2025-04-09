from flask import Flask, request, jsonify
import sqlite3
import hashlib
import secrets

app = Flask(__name__)
DB_FILE = "users.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                token TEXT
            )
        """)
        conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    return secrets.token_hex(16)

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Thiếu thông tin"}), 400

    password_hash = hash_password(password)
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            conn.commit()
        return jsonify({"message": "Đăng ký thành công"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Tên người dùng đã tồn tại"}), 409

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    password_hash = hash_password(password)
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, password_hash))
        result = c.fetchone()
        if result:
            token = generate_token()
            c.execute("UPDATE users SET token=? WHERE id=?", (token, result[0]))
            conn.commit()
            return jsonify({"token": token})
        else:
            return jsonify({"error": "Sai thông tin đăng nhập"}), 401

@app.route("/me", methods=["GET"])
def get_user():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Thiếu token"}), 401

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE token=?", (token,))
        result = c.fetchone()
        if result:
            return jsonify({"id": result[0], "username": result[1]})
        else:
            return jsonify({"error": "Token không hợp lệ"}), 403

if __name__ == "__main__":
    init_db()
    app.run(port=6000)
