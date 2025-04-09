
import os
import hashlib
import json
import socket
import requests
import threading
import time
from flask import Flask, request, jsonify
from collections import defaultdict

# ========== CONFIG ==========
TRACKER_PORT = 5000
TRACKER_URL = f"http://localhost:{TRACKER_PORT}"
SHARED_FOLDER = "shared"
TORRENT_FOLDER = "torrents"
DOWNLOAD_FOLDER = "downloads"
PIECE_LENGTH = 512

# ========== TIỆN ÍCH ==========
def sha1(data):
    return hashlib.sha1(data).hexdigest()

def ensure_dirs():
    os.makedirs(SHARED_FOLDER, exist_ok=True)
    os.makedirs(TORRENT_FOLDER, exist_ok=True)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ========== TRACKER ==========
def start_tracker():
    app = Flask(__name__)
    torrents = defaultdict(list)

    @app.route('/announce', methods=['POST'])
    def announce():
        data = request.json
        info_hash = data['info_hash']
        peer = {'peer_id': data['peer_id'], 'ip': data['ip'], 'port': data['port']}
        event = data['event']
        if event == 'started':
            if peer not in torrents[info_hash]:
                torrents[info_hash].append(peer)
            return jsonify({'status': 'registered', 'peers': torrents[info_hash]})
        elif event == 'stopped':
            if peer in torrents[info_hash]:
                torrents[info_hash].remove(peer)
            return jsonify({'status': 'removed'})
        return jsonify({'status': 'ignored'})

    @app.route('/peers', methods=['GET'])
    def get_peers():
        info_hash = request.args.get('info_hash')
        return jsonify({'info_hash': info_hash, 'peers': torrents.get(info_hash, [])})

    app.run(host='127.0.0.1', port=TRACKER_PORT)

# ========== UPLOAD ==========
def create_torrent(file_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    pieces = []

    with open(file_path, "rb") as f:
        while True:
            block = f.read(PIECE_LENGTH)
            if not block:
                break
            pieces.append(sha1(block))

    info = {
        "file_name": file_name,
        "file_size": file_size,
        "piece_length": PIECE_LENGTH,
        "pieces": pieces
    }
    info_hash = sha1(json.dumps(info, sort_keys=True).encode())

    torrent = {
        "info_hash": info_hash,
        "tracker_url": TRACKER_URL,
        "info": info
    }

    torrent_path = os.path.join(TORRENT_FOLDER, file_name + ".torrent")
    with open(torrent_path, "w") as f:
        json.dump(torrent, f, indent=4)

    return torrent, torrent_path

def run_seeder(torrent):
    info_hash = torrent["info_hash"]
    piece_length = torrent["info"]["piece_length"]
    file_path = os.path.join(SHARED_FOLDER, torrent["info"]["file_name"])
    shared_data = {}
    with open(file_path, "rb") as f:
        i = 0
        while True:
            piece = f.read(piece_length)
            if not piece:
                break
            if info_hash not in shared_data:
                shared_data[info_hash] = {}
            shared_data[info_hash][i] = piece
            i += 1

    data = {
        "info_hash": info_hash,
        "peer_id": "seeder001",
        "ip": "127.0.0.1",
        "port": 6881,
        "event": "started"
    }
    try:
        requests.post(f"{TRACKER_URL}/announce", json=data)
    except:
        print("⚠️ Không thể kết nối tracker.")

    def handle_client(conn, addr):
        data = conn.recv(1024).decode()
        parts = data.strip().split("|")
        if len(parts) != 2:
            conn.sendall(b"INVALID")
            return
        info_hash_req, index = parts[0], int(parts[1])
        piece = shared_data.get(info_hash_req, {}).get(index)
        if piece:
            conn.sendall(piece)
        else:
            conn.sendall(b"NOT_FOUND")
        conn.close()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 6881))
    s.listen(5)
    print("📡 Seeder đang chia sẻ file...")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

# ========== DOWNLOAD ==========
def download_from_torrent(torrent_path):
    with open(torrent_path, "r") as f:
        torrent = json.load(f)

    info = torrent["info"]
    info_hash = torrent["info_hash"]
    total_pieces = len(info["pieces"])
    result_buffer = [None] * total_pieces

    try:
        r = requests.get(f"{TRACKER_URL}/peers", params={"info_hash": info_hash})
        peers = r.json().get("peers", [])
    except:
        print("❌ Không thể lấy danh sách Seeder.")
        return

    def download_piece(i):
        for peer in peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((peer["ip"], peer["port"]))
                s.sendall(f"{info_hash}|{i}".encode())
                data = s.recv(4096)
                s.close()
                if sha1(data) == info["pieces"][i]:
                    result_buffer[i] = data
                    print(f"✅ Piece {i} tải thành công.")
                    return
            except:
                continue

    threads = []
    for i in range(total_pieces):
        t = threading.Thread(target=download_piece, args=(i,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    if None in result_buffer:
        print("❌ Một số piece không tải được.")
        return

    out_path = os.path.join(DOWNLOAD_FOLDER, "downloaded_" + info["file_name"])
    with open(out_path, "wb") as f:
        for p in result_buffer:
            f.write(p)
    print(f"🎉 Đã tải thành công: {out_path}")

# ========== MAIN MENU ==========
def main():
    ensure_dirs()
    threading.Thread(target=start_tracker, daemon=True).start()
    time.sleep(1)

    while True:
        print("""\n📁 P2P File Sharing Menu
1. 📤 Upload (chia sẻ file)
2. 📥 Download (tải từ .torrent)
3. ❌ Thoát
""")
        choice = input("→ Bạn chọn: ").strip()
        if choice == "1":
            files = os.listdir(SHARED_FOLDER)
            if not files:
                print("⚠️ Không có file nào trong 'shared/'. Hãy thêm file trước.")
                continue
            print("📂 Danh sách file trong shared/:")
            for i, f in enumerate(files):
                print(f"{i+1}. {f}")
            index = int(input("Chọn file để upload: ")) - 1
            file_path = os.path.join(SHARED_FOLDER, files[index])
            torrent, path = create_torrent(file_path)
            print(f"✅ Tạo .torrent: {path}")
            print("🚀 Đang chạy Seeder...")
            threading.Thread(target=run_seeder, args=(torrent,), daemon=True).start()

        elif choice == "2":
            files = os.listdir(TORRENT_FOLDER)
            if not files:
                print("⚠️ Không có file .torrent nào.")
                continue
            print("📂 Danh sách file .torrent:")
            for i, f in enumerate(files):
                print(f"{i+1}. {f}")
            index = int(input("Chọn file để download: ")) - 1
            torrent_path = os.path.join(TORRENT_FOLDER, files[index])
            download_from_torrent(torrent_path)

        elif choice == "3":
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
