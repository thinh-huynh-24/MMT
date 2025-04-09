
import os
import json
import hashlib
import socket
import threading
import requests

TRACKER_URL = "http://tracker:5000"
SHARED_FOLDER = "shared"
FILE_NAME = "example.txt"
PIECE_LENGTH = 512
PORT = 6881

def sha1(data):
    return hashlib.sha1(data).hexdigest()

def create_torrent(file_path):
    file_size = os.path.getsize(file_path)
    pieces = []

    with open(file_path, "rb") as f:
        while True:
            block = f.read(PIECE_LENGTH)
            if not block:
                break
            pieces.append(sha1(block))

    info = {
        "file_name": FILE_NAME,
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

    return torrent, info_hash, info

def register_with_tracker(info_hash):
    data = {
        "info_hash": info_hash,
        "peer_id": "seeder001",
        "ip": "seeder",  # container name
        "port": PORT,
        "event": "started"
    }
    requests.post(f"{TRACKER_URL}/announce", json=data)

def run_seeder(torrent, info_hash, info):
    file_path = os.path.join(SHARED_FOLDER, FILE_NAME)
    shared_data = {}

    with open(file_path, "rb") as f:
        i = 0
        while True:
            piece = f.read(info["piece_length"])
            if not piece:
                break
            shared_data[i] = piece
            i += 1

    def handle_client(conn, addr):
        try:
            data = conn.recv(1024).decode()
            parts = data.strip().split("|")
            if len(parts) != 2:
                conn.sendall(b"INVALID")
                return
            req_hash, index = parts[0], int(parts[1])
            if req_hash != info_hash:
                conn.sendall(b"HASH_MISMATCH")
                return
            if index in shared_data:
                conn.sendall(shared_data[index])
            else:
                conn.sendall(b"PIECE_NOT_FOUND")
        finally:
            conn.close()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", PORT))
    s.listen(5)
    print(f"Seeder đang chạy tại cổng {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    file_path = os.path.join(SHARED_FOLDER, FILE_NAME)
    torrent, info_hash, info = create_torrent(file_path)
    register_with_tracker(info_hash)
    run_seeder(torrent, info_hash, info)
