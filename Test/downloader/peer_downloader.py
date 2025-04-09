
import os
import json
import hashlib
import socket
import threading
import requests

TRACKER_URL = "http://tracker:5000"
TORRENT_PATH = "torrents/example.txt.torrent"
DOWNLOAD_FOLDER = "downloads"

def sha1(data):
    return hashlib.sha1(data).hexdigest()

def get_peers(info_hash):
    try:
        res = requests.get(f"{TRACKER_URL}/peers", params={"info_hash": info_hash})
        return res.json().get("peers", [])
    except Exception as e:
        print("❌ Không thể lấy danh sách peers:", e)
        return []

def download_piece(ip, port, info_hash, index):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(f"{info_hash}|{index}".encode())
            return s.recv(4096)
    except Exception as e:
        print(f"⚠️ Lỗi tải piece {index} từ {ip}:{port} - {e}")
        return None

def download_file():
    with open(TORRENT_PATH, "r") as f:
        torrent = json.load(f)

    info = torrent["info"]
    info_hash = torrent["info_hash"]
    total_pieces = len(info["pieces"])
    result_buffer = [None] * total_pieces
    peers = get_peers(info_hash)

    def worker(i):
        for peer in peers:
            ip, port = peer["ip"], peer["port"]
            data = download_piece(ip, port, info_hash, i)
            if data and sha1(data) == info["pieces"][i]:
                result_buffer[i] = data
                print(f"✅ Piece {i} tải thành công từ {ip}:{port}")
                return

    threads = []
    for i in range(total_pieces):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    if None in result_buffer:
        print("❌ Một số pieces không tải được.")
        return

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    out_path = os.path.join(DOWNLOAD_FOLDER, "downloaded_" + info["file_name"])
    with open(out_path, "wb") as f:
        for piece in result_buffer:
            f.write(piece)
    print(f"🎉 Đã tải thành công: {out_path}")

if __name__ == "__main__":
    download_file()
