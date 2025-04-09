import socket
import threading
import json
import os
import requests

AUTH_API_URL = "http://localhost:6000/login"
USERNAME = "thinh"
PASSWORD = "123456"
TOKEN = None

def login_and_get_token():
    global TOKEN
    try:
        res = requests.post(AUTH_API_URL, json={"username": USERNAME, "password": PASSWORD})
        if res.status_code == 200:
            TOKEN = res.json()["token"]
            print(f"✅ Đăng nhập thành công. Token: {TOKEN}")
        else:
            print(f"❌ Đăng nhập thất bại: {res.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối tới auth API: {e}")

def load_shared_data(torrent_path="torrents/example.txt.torrent"):
    with open(torrent_path, "r") as f:
        torrent = json.load(f)

    file_name = torrent["info"]["file_name"]
    piece_length = torrent["info"]["piece_length"]
    info_hash = torrent["info_hash"]
    file_path = os.path.join("shared", file_name)

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
    return shared_data, info_hash, torrent["tracker_url"]

def register_with_tracker(info_hash, tracker_url, peer_id="seeder001", ip="127.0.0.1", port=6881):
    if not TOKEN:
        print("❌ Không có token xác thực. Dừng đăng ký.")
        return

    data = {
        "info_hash": info_hash,
        "peer_id": peer_id,
        "ip": ip,
        "port": port,
        "event": "started",
        "token": TOKEN
    }

    try:
        res = requests.post(f"{tracker_url}/announce", json=data)
        if res.status_code == 200:
            print("✅ Đã đăng ký với tracker!")
        else:
            print("❌ Tracker từ chối:", res.text)
    except Exception as e:
        print("❌ Lỗi kết nối tracker:", e)

def handle_client(conn, addr, SHARED_DATA):
    print(f"📥 Kết nối từ {addr}")
    try:
        data = conn.recv(1024).decode()
        parts = data.strip().split("|")
        if len(parts) != 2:
            conn.sendall(b"INVALID_FORMAT")
            return

        info_hash, piece_index = parts[0], int(parts[1])
        if info_hash in SHARED_DATA and piece_index in SHARED_DATA[info_hash]:
            piece_data = SHARED_DATA[info_hash][piece_index]
            conn.sendall(piece_data)
        else:
            conn.sendall(b"PIECE_NOT_FOUND")
    finally:
        conn.close()

def start_server(port=6881):
    login_and_get_token()
    SHARED_DATA, info_hash, tracker_url = load_shared_data()
    register_with_tracker(info_hash, tracker_url, port=port)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", port))
    server.listen(5)
    print(f"📡 Seeder đang lắng nghe tại cổng {port}...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr, SHARED_DATA))
        thread.start()

if __name__ == "__main__":
    os.makedirs("shared", exist_ok=True)
    start_server()
