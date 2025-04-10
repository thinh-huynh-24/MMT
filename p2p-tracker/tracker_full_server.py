from flask import Flask, request, jsonify, render_template_string
import sqlite3, hashlib, secrets
from collections import defaultdict

app = Flask(__name__)
DB_FILE = "users.db"
torrents = defaultdict(list)
stats = defaultdict(lambda: {"uploads": {}, "downloads": {}})

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

def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def generate_token(): return secrets.token_hex(16)

def get_user_id_by_token(token):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE token=?", (token,))
        r = c.fetchone()
        return r[0] if r else None

@app.route("/register", methods=["POST"])
def register():
    d = request.get_json()
    u, p = d.get("username"), d.get("password")
    if not u or not p: return jsonify({"error": "Thiếu thông tin"}), 400
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (u, hash_password(p)))
            conn.commit()
        return jsonify({"message": "Đăng ký thành công"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Tài khoản đã tồn tại"}), 409

@app.route("/login", methods=["POST"])
def login():
    d = request.get_json()
    u, p = d.get("username"), d.get("password")
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (u, hash_password(p)))
        r = c.fetchone()
        if r:
            token = generate_token()
            c.execute("UPDATE users SET token=? WHERE id=?", (token, r[0]))
            conn.commit()
            return jsonify({"token": token})
        return jsonify({"error": "Sai thông tin"}), 401

@app.route("/announce", methods=["POST"])
def announce():
    d = request.get_json()
    token = d.get("token")
    user_id = get_user_id_by_token(token)
    if not user_id: return jsonify({"error": "unauthorized"}), 401

    info_hash = d.get("info_hash")
    peer = {"peer_id": d.get("peer_id"), "ip": d.get("ip"), "port": d.get("port")}
    event = d.get("event", "started")

    if event == "started":
        if peer not in torrents[info_hash]:
            torrents[info_hash].append(peer)
        return jsonify({"status": "registered", "peers": torrents[info_hash]})
    elif event == "stopped":
        if peer in torrents[info_hash]:
            torrents[info_hash].remove(peer)
        return jsonify({"status": "removed"})
    elif event == "upload":
        stats[info_hash]["uploads"][user_id] = stats[info_hash]["uploads"].get(user_id, 0) + 1
        return jsonify({"status": "upload_counted"})
    elif event == "download":
        stats[info_hash]["downloads"][user_id] = stats[info_hash]["downloads"].get(user_id, 0) + 1
        return jsonify({"status": "download_counted"})
    return jsonify({"status": "ignored"})

@app.route("/peers", methods=["GET"])
def get_peers():
    info_hash = request.args.get("info_hash")
    return jsonify({"info_hash": info_hash, "peers": torrents.get(info_hash, [])})

@app.route("/stats", methods=["GET"])
def get_stats():
    info_hash = request.args.get("info_hash")
    return jsonify(stats[info_hash])

@app.route("/peers/list", methods=["GET"])
def list_peers():
    html = """
    <h2>📡 Danh sách các Peers đang đăng ký</h2>
    {% if torrents %}
        {% for info_hash, peers in torrents.items() %}
            <h4>📁 Info Hash: {{ info_hash }}</h4>
            <ul>
                {% for peer in peers %}
                    <li>🧑 Peer ID: {{ peer['peer_id'] }} | IP: {{ peer['ip'] }} | Port: {{ peer['port'] }}</li>
                {% endfor %}
            </ul>
        {% endfor %}
    {% else %}
        <p>❌ Không có peer nào đang hoạt động.</p>
    {% endif %}
    """
    return render_template_string(html, torrents=torrents)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
