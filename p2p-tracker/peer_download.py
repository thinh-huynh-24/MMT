import socket
import json
import hashlib
import os
import requests
import threading

def sha1(data):
    return hashlib.sha1(data).hexdigest()

def get_peers_from_tracker(torrent):
    tracker_url = torrent["tracker_url"]
    info_hash = torrent["info_hash"]

    try:
        response = requests.get(f"{tracker_url}/peers", params={"info_hash": info_hash})
        data = response.json()
        return data.get("peers", [])
    except Exception as e:
        print(f"❌ Lỗi lấy danh sách peers: {e}")
        return []

def download_piece(ip, port, info_hash, piece_index):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            request = f"{info_hash}|{piece_index}"
            s.sendall(request.encode())
            data = s.recv(4096)
            return data
    except Exception as e:
        print(f"❌ Lỗi khi kết nối tới {ip}:{port} - {e}")
        return None

def download_file_from_torrent(torrent_file_path):
    with open(torrent_file_path, "r") as f:
        torrent = json.load(f)

    info_hash = torrent["info_hash"]
    info = torrent["info"]
    expected_pieces = info["pieces"]
    total_pieces = len(expected_pieces)

    peers = get_peers_from_tracker(torrent)
    if not peers:
        print("❌ Không tìm thấy Seeder từ tracker.")
        return

    os.makedirs("downloads", exist_ok=True)
    output_path = os.path.join("downloads", "downloaded_" + info["file_name"])
    result_buffer = [None] * total_pieces
    lock = threading.Lock()

    def download_piece_thread(i):
        nonlocal result_buffer
        for peer in peers:
            ip = peer["ip"]
            port = peer["port"]
            try:
                print(f"🔗 [Thread-{i}] Thử tải piece {i} từ {ip}:{port}")
                data = download_piece(ip, port, info_hash, i)
                if data and sha1(data) == expected_pieces[i]:
                    with lock:
                        result_buffer[i] = data
                    print(f"✅ [Thread-{i}] Piece {i} hợp lệ từ {ip}")
                    return
                else:
                    print(f"⚠️ [Thread-{i}] Hash không đúng từ {ip}")
            except Exception as e:
                print(f"❌ [Thread-{i}] Lỗi từ {ip}:{port} - {e}")

    threads = []
    for i in range(total_pieces):
        t = threading.Thread(target=download_piece_thread, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    if None in result_buffer:
        print("❌ Một số pieces không tải được.")
        return

    with open(output_path, "wb") as f:
        for piece in result_buffer:
            f.write(piece)

    print(f"\n✅ Hoàn tất tải file song song! Lưu tại: {output_path}")

if __name__ == "__main__":
    os.makedirs("torrents", exist_ok=True)
    download_file_from_torrent("torrents/example.txt.torrent")
