import os
import json
import socket
import threading
import hashlib

SHARED_FOLDER = "shared"
PIECE_LENGTH = 512

def sha1(data): return hashlib.sha1(data).hexdigest()

def load_torrent(torrent_path):
    with open(torrent_path, "r") as f:
        return json.load(f)

def prepare_piece_data(torrent):
    info = torrent["info"]
    piece_len = info["piece_length"]
    data, buffer, index = {}, b"", 0

    if "file_name" in info:
        path = os.path.join(SHARED_FOLDER, info["file_name"])
        with open(path, "rb") as f:
            while chunk := f.read(4096):
                buffer += chunk
                while len(buffer) >= piece_len:
                    data[index] = buffer[:piece_len]
                    buffer = buffer[piece_len:]
                    index += 1
    else:
        for file in info["files"]:
            path = os.path.join(SHARED_FOLDER, info["folder_name"], file["path"])
            with open(path, "rb") as f:
                while chunk := f.read(4096):
                    buffer += chunk
                    while len(buffer) >= piece_len:
                        data[index] = buffer[:piece_len]
                        buffer = buffer[piece_len:]
                        index += 1
    if buffer:
        data[index] = buffer
    return data

def run_seeder(torrent_path):
    torrent = load_torrent(torrent_path)
    info_hash = torrent["info_hash"]
    piece_data = prepare_piece_data(torrent)

    def handle_client(conn, addr):
        try:
            msg = conn.recv(1024).decode()
            parts = msg.strip().split("|")
            if len(parts) != 2 or parts[0] != info_hash:
                conn.sendall(b"INVALID")
                return
            index = int(parts[1])
            conn.sendall(piece_data.get(index, b"NOT_FOUND"))
            print(f"📤 Gửi piece {index} cho {addr}")
        except Exception as e:
            print(f"⚠️ Lỗi client {addr}: {e}")
        finally:
            conn.close()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 6881))
    s.listen(5)
    print("📡 Seeder đã sẵn sàng, chờ peer kết nối...")

    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()
    except KeyboardInterrupt:
        print("🛑 Dừng Seeder.")

if __name__ == "__main__":
    path = input("📦 Nhập đường dẫn file .torrent: ").strip()
    run_seeder(path)
