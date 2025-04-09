from flask import Flask, request, jsonify
from collections import defaultdict
import sqlite3

app = Flask(__name__)
torrents = defaultdict(list)  # info_hash -> list of peers
stats = defaultdict(lambda: {"uploads": {}, "downloads": {}})  # info_hash -> user_id -> count
DB_FILE = "users.db"

def get_user_id_by_token(token):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE token=?", (token,))
        result = c.fetchone()
        return result[0] if result else None

@app.route('/announce', methods=['POST'])
def announce():
    data = request.json
    token = data.get("token")
    user_id = get_user_id_by_token(token)
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    info_hash = data["info_hash"]
    peer_id = data["peer_id"]
    ip = data["ip"]
    port = data["port"]
    event = data.get("event", "started")

    peer = {
        "peer_id": peer_id,
        "ip": ip,
        "port": port,
        "user_id": user_id
    }

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

@app.route('/peers', methods=['GET'])
def get_peers():
    info_hash = request.args.get("info_hash")
    return jsonify({
        "info_hash": info_hash,
        "peers": torrents.get(info_hash, [])
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    info_hash = request.args.get("info_hash")
    return jsonify({
        "info_hash": info_hash,
        "uploads": stats[info_hash]["uploads"],
        "downloads": stats[info_hash]["downloads"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
