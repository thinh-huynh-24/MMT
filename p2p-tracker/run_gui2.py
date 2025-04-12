import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import json
import requests
import socket
import hashlib
import random

# ==== Cấu hình ====
TRACKER_URL = ""
TOKEN = ""
PIECE_LENGTH = 512
SHARED_FOLDER = "shared"
TORRENT_FOLDER = "torrents"
DOWNLOAD_FOLDER = "downloads"
PROGRESS_FOLDER = os.path.join(DOWNLOAD_FOLDER, ".progress")

def sha1(data): return hashlib.sha1(data).hexdigest()

def ensure_dirs():
    for folder in [SHARED_FOLDER, TORRENT_FOLDER, DOWNLOAD_FOLDER, PROGRESS_FOLDER]:
        os.makedirs(folder, exist_ok=True)

def save_progress(info_hash, bitmap):
    with open(os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress"), "w") as f:
        json.dump(bitmap, f)

def load_progress(info_hash, total):
    path = os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress")
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return [False] * total

class P2PGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌐 P2P File Sharing")
        self.geometry("520x460")
        self.protocol("WM_DELETE_WINDOW", self.quit)
        ensure_dirs()
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Tracker URL:").pack()
        self.entry_tracker = tk.Entry(self, width=50)
        self.entry_tracker.insert(0, "http://localhost:5000")
        self.entry_tracker.pack()

        tk.Label(self, text="Username:").pack()
        self.entry_user = tk.Entry(self, width=30)
        self.entry_user.pack()

        tk.Label(self, text="Password:").pack()
        self.entry_pass = tk.Entry(self, show="*", width=30)
        self.entry_pass.pack()

        self.btn_login = tk.Button(self, text="🔐 Đăng nhập", command=self.login)
        self.btn_login.pack(pady=5)

        self.btn_upload_folder = tk.Button(self, text="📤 Upload Thư mục", command=self.upload_folder, state="disabled")
        self.btn_upload_folder.pack(pady=5)

        self.btn_upload_file = tk.Button(self, text="📤 Upload File", command=self.upload_file, state="disabled")
        self.btn_upload_file.pack(pady=5)

        self.btn_download = tk.Button(self, text="📥 Download từ .torrent", command=self.download_torrent, state="disabled")
        self.btn_download.pack(pady=5)

        self.status = tk.Label(self, text="⚠️ Chưa đăng nhập", fg="blue")
        self.status.pack(pady=10)

        self.progress = ttk.Progressbar(self, length=300, mode='determinate')
        self.progress.pack(pady=5)

    def login(self):
        global TRACKER_URL, TOKEN
        TRACKER_URL = self.entry_tracker.get().strip()
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        try:
            r = requests.post(f"{TRACKER_URL}/login", json={"username": username, "password": password})
            if r.status_code == 200:
                TOKEN = r.json()["token"]
                self.status.config(text="✅ Đăng nhập thành công", fg="green")
                self.btn_upload_folder.config(state="normal")
                self.btn_upload_file.config(state="normal")
                self.btn_download.config(state="normal")
            else:
                self.status.config(text="❌ Sai thông tin", fg="red")
        except Exception as e:
            self.status.config(text=f"❌ Lỗi: {e}", fg="red")

    def upload_file(self):
        file_path = filedialog.askopenfilename(initialdir=SHARED_FOLDER)
        if not file_path: return
        name = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        pieces = []
        with open(file_path, "rb") as f:
            while chunk := f.read(PIECE_LENGTH):
                pieces.append(sha1(chunk))
        info = {"file_name": name, "file_size": size, "piece_length": PIECE_LENGTH, "pieces": pieces}
        info_hash = sha1(json.dumps(info, sort_keys=True).encode())
        torrent = {"info_hash": info_hash, "tracker_url": TRACKER_URL, "info": info}
        with open(os.path.join(TORRENT_FOLDER, name + ".torrent"), "w") as f:
            json.dump(torrent, f, indent=4)
        messagebox.showinfo("✅ Upload", f"Đã tạo torrent: {name}.torrent")
        threading.Thread(target=self.run_seeder, args=(torrent, file_path), daemon=True).start()

    def upload_folder(self):
        folder_path = filedialog.askdirectory(initialdir=SHARED_FOLDER)
        if not folder_path: return
        all_data = b""
        pieces = []
        files = []
        for root, _, filenames in os.walk(folder_path):
            for fname in filenames:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, folder_path).replace("\\", "/")
                length = os.path.getsize(full_path)
                files.append({"path": rel_path, "length": length})
                with open(full_path, "rb") as f:
                    all_data += f.read()
        for i in range(0, len(all_data), PIECE_LENGTH):
            pieces.append(sha1(all_data[i:i+PIECE_LENGTH]))
        folder_name = os.path.basename(folder_path)
        info = {"folder_name": folder_name, "files": files, "piece_length": PIECE_LENGTH, "pieces": pieces}
        info_hash = sha1(json.dumps(info, sort_keys=True).encode())
        torrent = {"info_hash": info_hash, "tracker_url": TRACKER_URL, "info": info}
        with open(os.path.join(TORRENT_FOLDER, folder_name + ".torrent"), "w") as f:
            json.dump(torrent, f, indent=4)
        messagebox.showinfo("✅ Upload", f"Đã tạo torrent: {folder_name}.torrent")
        threading.Thread(target=self.run_seeder, args=(torrent, folder_path), daemon=True).start()

    def run_seeder(self, torrent, path):
        info = torrent["info"]
        info_hash = torrent["info_hash"]
        data, buffer, i = {}, b"", 0
        if "file_name" in info:
            # single file
            with open(path, "rb") as f:
                while chunk := f.read(4096):
                    buffer += chunk
                    while len(buffer) >= info["piece_length"]:
                        data[i] = buffer[:info["piece_length"]]
                        buffer = buffer[info["piece_length"]:]
                        i += 1
            if buffer: data[i] = buffer
        else:
            # folder
            for fmeta in info["files"]:
                fpath = os.path.join(path, fmeta["path"].replace("/", os.sep))
                with open(fpath, "rb") as f:
                    buffer += f.read()
            for i in range(0, len(buffer), info["piece_length"]):
                data[i//info["piece_length"]] = buffer[i:i+info["piece_length"]]

        port = random.randint(10000, 60000)
        try:
            requests.post(f"{TRACKER_URL}/announce", json={
                "info_hash": info_hash, "peer_id": "gui_seeder", "ip": "127.0.0.1",
                "port": port, "event": "started", "token": TOKEN
            })
        except:
            print("⚠ Không kết nối được tracker")

        def handle(conn, addr):
            try:
                msg = conn.recv(1024).decode()
                h, idx = msg.split("|")
                piece = data.get(int(idx))
                conn.sendall(piece if piece else b"NOT_FOUND")
            finally:
                conn.close()

        s = socket.socket(); s.bind(("0.0.0.0", port)); s.listen(5)
        while True:
            threading.Thread(target=handle, args=s.accept()).start()

    def download_torrent(self):
        torrent_path = filedialog.askopenfilename(initialdir=TORRENT_FOLDER)
        if not torrent_path: return
        with open(torrent_path) as f:
            torrent = json.load(f)
        info = torrent["info"]
        info_hash = torrent["info_hash"]
        total = len(info["pieces"])
        filename = info.get("file_name", info.get("folder_name", "downloaded"))
        peers = requests.get(f"{TRACKER_URL}/peers", params={"info_hash": info_hash}).json()["peers"]
        bitmap = load_progress(info_hash, total)

        def download_piece(i):
            if bitmap[i]: return
            for peer in peers:
                try:
                    s = socket.socket(); s.connect((peer["ip"], peer["port"]))
                    s.sendall(f"{info_hash}|{i}".encode())
                    data = s.recv(4096); s.close()
                    if sha1(data) == info["pieces"][i]:
                        with open(f"{DOWNLOAD_FOLDER}/{filename}.part{i}", "wb") as f:
                            f.write(data)
                        bitmap[i] = True
                        save_progress(info_hash, bitmap)
                        self.progress["value"] = 100 * sum(bitmap) / total
                        return
                except: continue

        def run_download():
            threads = [threading.Thread(target=download_piece, args=(i,)) for i in range(total)]
            [t.start() for t in threads]
            [t.join() for t in threads]

            if not all(bitmap):
                messagebox.showwarning("⚠️", "Một số phần chưa tải xong.")
                return

            out_path = os.path.join(DOWNLOAD_FOLDER, "downloaded_" + filename)
            with open(out_path, "wb") as out:
                for i in range(total):
                    part_path = f"{DOWNLOAD_FOLDER}/{filename}.part{i}"
                    with open(part_path, "rb") as pf:
                        out.write(pf.read())
                    os.remove(part_path)
            messagebox.showinfo("🎉 Xong", f"File đã lưu tại: {out_path}")

        threading.Thread(target=run_download, daemon=True).start()

if __name__ == "__main__":
    app = P2PGUI()
    app.mainloop()
