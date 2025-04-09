import os
import hashlib
import json

def sha1(data):
    return hashlib.sha1(data).hexdigest()

def create_torrent(file_path, tracker_url="http://localhost:5000", piece_length=512):
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    pieces = []

    with open(file_path, "rb") as f:
        while True:
            block = f.read(piece_length)
            if not block:
                break
            piece_hash = sha1(block)
            pieces.append(piece_hash)

    info = {
        "file_name": file_name,
        "file_size": file_size,
        "piece_length": piece_length,
        "pieces": pieces
    }

    info_hash = sha1(json.dumps(info, sort_keys=True).encode())

    torrent = {
        "info_hash": info_hash,
        "tracker_url": tracker_url,
        "info": info
    }

    os.makedirs("torrents", exist_ok=True)
    torrent_file_path = os.path.join("torrents", file_name + ".torrent")
    with open(torrent_file_path, "w") as f:
        json.dump(torrent, f, indent=4)

    print(f"📦 Torrent file tạo tại: {torrent_file_path}")
    print(f"🧬 info_hash: {info_hash}")
    return torrent

if __name__ == "__main__":
    os.makedirs("shared", exist_ok=True)
    file_path = os.path.join("shared", "example.txt")
    create_torrent(file_path)
