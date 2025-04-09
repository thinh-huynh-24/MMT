import os
import requests
import getpass

# === Cấu hình địa chỉ máy chủ Tracker ===
TRACKER_IP = "localhost"  # Nếu Tracker ở máy khác → thay bằng IP, ví dụ: "192.168.1.10"
TRACKER_PORT = "5000"
TRACKER_URL = f"http://{TRACKER_IP}:{TRACKER_PORT}"
AUTH_API = TRACKER_URL

def login():
    print("🔐 Đăng nhập")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    try:
        res = requests.post(f"{AUTH_API}/login", json={"username": username, "password": password})
        if res.status_code == 200:
            token = res.json()["token"]
            print("✅ Đăng nhập thành công!")
            return token, username
        else:
            print("❌ Sai thông tin đăng nhập.")
    except Exception as e:
        print("❌ Lỗi kết nối:", e)
    return None, None

def upload_folder(token):
    folder = input("📂 Nhập đường dẫn thư mục cần chia sẻ (ví dụ: shared/myfolder): ")
    if not os.path.isdir(folder):
        print("❌ Thư mục không tồn tại.")
        return
    os.makedirs("shared", exist_ok=True)

    print("🚧 Đang tạo .torrent file...")
    os.system(f"python torrent_creator.py \"{folder}\"")

    print("🚀 Khởi động Seeder...")
    os.system("python peer_server.py")

def download_file(token):
    torrent_file = input("📥 Nhập đường dẫn .torrent file (ví dụ: torrents/myfolder.torrent): ")
    if not os.path.isfile(torrent_file):
        print("❌ File không tồn tại.")
        return
    os.makedirs("downloads", exist_ok=True)

    print("🚀 Đang tải file...")
    os.system("python peer_download.py")

def main():
    print("🎉 Hệ thống chia sẻ tệp tin P2P")
    token, username = login()
    if not token:
        return

    while True:
        print(f"\n👋 Xin chào {username} - Chọn chức năng:")
        print("1. Tải tệp lên (Seeder)")
        print("2. Tải tệp xuống (Downloader)")
        print("0. Thoát")
        choice = input("→ Bạn chọn: ")

        if choice == "1":
            upload_folder(token)
        elif choice == "2":
            download_file(token)
        elif choice == "0":
            break
        else:
            print("⚠️ Vui lòng chọn lại.")

if __name__ == "__main__":
    main()
