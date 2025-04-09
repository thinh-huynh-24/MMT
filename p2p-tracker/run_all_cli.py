# run_all_cli.py
import os, json, socket, threading, time, requests, hashlib

TRACKER_URL = input("🌐 Nhập địa chỉ Tracker (vd: http://localhost:5000): ").strip()
SHARED_FOLDER = "shared"
TORRENT_FOLDER = "torrents"
DOWNLOAD_FOLDER = "downloads"
PIECE_LENGTH = 512
TOKEN = ""

def sha1(data): return hashlib.sha1(data).hexdigest()
def ensure_dirs():
    os.makedirs(SHARED_FOLDER, exist_ok=True)
    os.makedirs(TORRENT_FOLDER, exist_ok=True)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    os.makedirs("downloads/.progress", exist_ok=True)

def login():
    global TOKEN
    print("🔐 Đăng nhập")
    u = input("Username: ")
    p = input("Password: ")
    try:
        r = requests.post(f"{TRACKER_URL}/login", json={"username": u, "password": p})
        if r.status_code == 200:
            TOKEN = r.json()["token"]
            print("✅ Đăng nhập thành công.")
        else:
            print("❌ Thất bại:", r.text)
    except Exception as e:
        print("❌ Lỗi:", e)

def create_torrent(path):
    if os.path.isdir(path):
        return create_torrent_folder(path)
    return create_torrent_file(path)

def create_torrent_file(path):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    pieces, i = [], 0
    with open(path, "rb") as f:
        while chunk := f.read(PIECE_LENGTH):
            pieces.append(sha1(chunk))
            i += 1
    info = {"file_name": name, "file_size": size, "piece_length": PIECE_LENGTH, "pieces": pieces}
    info_hash = sha1(json.dumps(info, sort_keys=True).encode())
    torrent = {"info_hash": info_hash, "tracker_url": TRACKER_URL, "info": info}
    os.makedirs(TORRENT_FOLDER, exist_ok=True)
    with open(f"{TORRENT_FOLDER}/{name}.torrent", "w") as f:
        json.dump(torrent, f, indent=4)
    return torrent, f"{TORRENT_FOLDER}/{name}.torrent"

def create_torrent_folder(path):
    files, pieces, buffer = [], [], b""
    for root, _, fnames in os.walk(path):
        for fname in fnames:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, path).replace("\\", "/")
            size = os.path.getsize(full)
            files.append({"path": rel, "length": size})
            with open(full, "rb") as f:
                while chunk := f.read(4096):
                    buffer += chunk
                    while len(buffer) >= PIECE_LENGTH:
                        pieces.append(sha1(buffer[:PIECE_LENGTH]))
                        buffer = buffer[PIECE_LENGTH:]
    if buffer: pieces.append(sha1(buffer))
    folder = os.path.basename(path)
    info = {"folder_name": folder, "piece_length": PIECE_LENGTH, "files": files, "pieces": pieces}
    info_hash = sha1(json.dumps(info, sort_keys=True).encode())
    torrent = {"info_hash": info_hash, "tracker_url": TRACKER_URL, "info": info}
    with open(f"{TORRENT_FOLDER}/{folder}.torrent", "w") as f:
        json.dump(torrent, f, indent=4)
    return torrent, f"{TORRENT_FOLDER}/{folder}.torrent"

def run_seeder(torrent):
    info = torrent["info"]
    info_hash = torrent["info_hash"]
    buffer, data, i = b"", {}, 0
    if "file_name" in info:
        p = os.path.join(SHARED_FOLDER, info["file_name"])
        with open(p, "rb") as f:
            while chunk := f.read(4096):
                buffer += chunk
                while len(buffer) >= info["piece_length"]:
                    data[i] = buffer[:info["piece_length"]]
                    buffer = buffer[info["piece_length"]:]
                    i += 1
    else:
        for fobj in info["files"]:
            path = os.path.join(SHARED_FOLDER, info["folder_name"], fobj["path"])
            with open(path, "rb") as f:
                while chunk := f.read(4096):
                    buffer += chunk
                    while len(buffer) >= info["piece_length"]:
                        data[i] = buffer[:info["piece_length"]]
                        buffer = buffer[info["piece_length"]:]
                        i += 1
    if buffer: data[i] = buffer

    requests.post(f"{TRACKER_URL}/announce", json={
        "info_hash": info_hash, "peer_id": "seeder001", "ip": "127.0.0.1",
        "port": 6881, "event": "started", "token": TOKEN
    })

    def handle(conn):
        try:
            msg = conn.recv(1024).decode()
            h, idx = msg.split("|")
            piece = data.get(int(idx))
            conn.sendall(piece if piece else b"NOT_FOUND")
        finally:
            conn.close()

    s = socket.socket(); s.bind(("0.0.0.0", 6881)); s.listen(5)
    print("📡 Seeder đang sẵn sàng...")
    while True: threading.Thread(target=handle, args=s.accept()).start()

def download_torrent(path):
    with open(path) as f: torrent = json.load(f)
    info = torrent["info"]; info_hash = torrent["info_hash"]
    total = len(info["pieces"]); result = [None]*total

    # Resume
    progress_path = f"downloads/.progress/{info_hash}.progress"
    bitmap = [False]*total
    if os.path.exists(progress_path):
        with open(progress_path) as pf: bitmap = json.load(pf)

    peers = requests.get(f"{TRACKER_URL}/peers", params={"info_hash": info_hash}).json()["peers"]

    def save_progress():
        with open(progress_path, "w") as pf: json.dump(bitmap, pf)

    def download_piece(i):
        if bitmap[i]: return
        for peer in peers:
            try:
                s = socket.socket(); s.connect((peer["ip"], peer["port"]))
                s.sendall(f"{info_hash}|{i}".encode())
                data = s.recv(4096); s.close()
                if sha1(data) == info["pieces"][i]:
                    result[i] = data; bitmap[i] = True
                    save_progress()
                    print(f"✅ Piece {i}")
                    return
            except: continue

    threads = [threading.Thread(target=download_piece, args=(i,)) for i in range(total)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    if not all(bitmap):
        print("⚠️ Một số phần chưa tải xong.")
        return

    out = os.path.join(DOWNLOAD_FOLDER, "downloaded_" + (info.get("file_name") or info["folder_name"]))
    if "file_name" in info:
        with open(out, "wb") as f:
            for b in result: f.write(b)
    else:
        buffer = b"".join(result); offset = 0
        for fobj in info["files"]:
            path = os.path.join(out, fobj["path"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(buffer[offset:offset+fobj["length"]])
            offset += fobj["length"]
    print("🎉 Tải hoàn tất!")

def main():
    ensure_dirs(); login(); time.sleep(1)
    while True:
        print("\\n📁 MENU\n1. Upload\n2. Download\n3. Thoát")
        c = input("→ Chọn: ")
        if c == "1":
            files = os.listdir(SHARED_FOLDER)
            for i, f in enumerate(files): print(f"{i+1}. {f}")
            idx = int(input("Chọn mục để chia sẻ: ")) - 1
            path = os.path.join(SHARED_FOLDER, files[idx])
            torrent, tpath = create_torrent(path)
            print("📦 Torrent:", tpath)
            threading.Thread(target=run_seeder, args=(torrent,), daemon=True).start()
        elif c == "2":
            tfs = os.listdir(TORRENT_FOLDER)
            for i, f in enumerate(tfs): print(f"{i+1}. {f}")
            idx = int(input("Chọn torrent: ")) - 1
            download_torrent(os.path.join(TORRENT_FOLDER, tfs[idx]))
        elif c == "3":
            break
        else:
            print("⚠️ Nhập sai.")

if __name__ == "__main__":
    main()
