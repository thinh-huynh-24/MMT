import socket, json, os, hashlib, threading, requests

TRACKER_URL = "http://localhost:5000"
DOWNLOAD_FOLDER = "downloads"
PROGRESS_FOLDER = os.path.join(DOWNLOAD_FOLDER, ".progress")
PIECE_LENGTH = 512

def sha1(data): return hashlib.sha1(data).hexdigest()

def load_torrent(torrent_path):
    with open(torrent_path, "r") as f:
        return json.load(f)

def get_peers(info_hash):
    try:
        r = requests.get(f"{TRACKER_URL}/peers", params={"info_hash": info_hash})
        return r.json().get("peers", [])
    except:
        return []

def resume_bitmap(info_hash, total_pieces):
    os.makedirs(PROGRESS_FOLDER, exist_ok=True)
    path = os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress")
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return [False] * total_pieces

def save_bitmap(info_hash, bitmap):
    path = os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress")
    with open(path, "w") as f: json.dump(bitmap, f)

def reconstruct(info, pieces_data):
    if "file_name" in info:
        out_path = os.path.join(DOWNLOAD_FOLDER, "downloaded_" + info["file_name"])
        with open(out_path, "wb") as f:
            for p in pieces_data: f.write(p)
        print(f"🎉 Đã tải: {out_path}")
    else:
        folder = os.path.join(DOWNLOAD_FOLDER, info["folder_name"])
        os.makedirs(folder, exist_ok=True)
        buffer = b"".join(pieces_data)
        offset = 0
        for fobj in info["files"]:
            path = os.path.join(folder, fobj["path"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(buffer[offset:offset+fobj["length"]])
            offset += fobj["length"]
        print(f"🎉 Đã tải thư mục: {folder}")

def download_from_torrent(torrent_path):
    torrent = load_torrent(torrent_path)
    info = torrent["info"]
    info_hash = torrent["info_hash"]
    peers = get_peers(info_hash)
    total = len(info["pieces"])
    pieces_data = [None] * total
    bitmap = resume_bitmap(info_hash, total)

    def download_piece(i):
        if bitmap[i]: return
        for peer in peers:
            try:
                s = socket.socket(); s.connect((peer["ip"], peer["port"]))
                s.sendall(f"{info_hash}|{i}".encode())
                data = s.recv(4096); s.close()
                if sha1(data) == info["pieces"][i]:
                    pieces_data[i] = data
                    bitmap[i] = True
                    save_bitmap(info_hash, bitmap)
                    print(f"✅ Piece {i} OK")
                    return
            except: continue

    threads = []
    for i in range(total):
        t = threading.Thread(target=download_piece, args=(i,))
        t.start(); threads.append(t)
    for t in threads: t.join()

    if not all(bitmap):
        print("⚠️ Một số piece chưa hoàn tất.")
        return

    reconstruct(info, pieces_data)
    try: os.remove(os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress"))
    except: pass

if __name__ == "__main__":
    path = input("📥 Nhập đường dẫn .torrent: ").strip()
    download_from_torrent(path)
