import os, json, hashlib

def sha1(data): return hashlib.sha1(data).hexdigest()

def create_torrent_folder(folder_path, tracker="http://localhost:5000", piece_length=512):
    files, pieces, buffer = [], [], b""
    for root, _, filenames in os.walk(folder_path):
        for name in filenames:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, folder_path).replace("\\", "/")
            length = os.path.getsize(abs_path)
            files.append({"path": rel_path, "length": length})
            with open(abs_path, "rb") as f:
                while chunk := f.read(4096):
                    buffer += chunk
                    while len(buffer) >= piece_length:
                        pieces.append(sha1(buffer[:piece_length]))
                        buffer = buffer[piece_length:]
    if buffer: pieces.append(sha1(buffer))
    folder = os.path.basename(folder_path)
    info = {"folder_name": folder, "piece_length": piece_length, "files": files, "pieces": pieces}
    info_hash = sha1(json.dumps(info, sort_keys=True).encode())
    torrent = {"info_hash": info_hash, "tracker_url": tracker, "info": info}
    os.makedirs("torrents", exist_ok=True)
    with open(f"torrents/{folder}.torrent", "w") as f: json.dump(torrent, f, indent=4)
    print(f"✅ Torrent created: torrents/{folder}.torrent")
    return torrent
