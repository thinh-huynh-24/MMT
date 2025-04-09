📁 HỆ THỐNG CHIA SẺ FILE P2P – HƯỚNG DẪN CHẠY
────────────────────────────────────────────

I. 📦 THÀNH PHẦN FILE

| Tên tệp              | Mục đích                                           |
|----------------------|----------------------------------------------------|
| tracker_full_server.py | Tracker Flask lưu Peer và xác thực người dùng     |
| run_all_cli.py         | Giao diện CLI: login, upload, download            |
| peer_server.py         | Seeder riêng: chia sẻ file                        |
| peer_download.py       | Downloader riêng: tải và resume                   |
| torrent_creator.py     | Tạo file .torrent từ file hoặc thư mục            |

II. 🛠 CÀI ĐẶT

Yêu cầu:
- Python >= 3.9
- Các thư viện:
    pip install flask requests

Cấu trúc thư mục:
- shared/: chứa file hoặc thư mục chia sẻ
- torrents/: chứa file .torrent đã tạo
- downloads/: chứa file tải về từ các peer
- downloads/.progress/: lưu tiến trình tải dở

III. 🚀 CÁCH CHẠY HỆ THỐNG

1. 🔗 CHẠY TRACKER SERVER
   - Trên máy chủ:
     python tracker_full_server.py
   - Tracker lắng nghe tại http://<IP>:5000

2. 🧑 ĐĂNG KÝ TÀI KHOẢN (qua API hoặc Thunder Client)
   - POST /register
   - Body:
     {
       "username": "user1",
       "password": "123456"
     }

3. 💻 PEER GIAO DIỆN CLI
   - Trên mỗi máy peer:
     python run_all_cli.py
   - Nhập IP tracker
   - Đăng nhập
   - Chọn Upload hoặc Download

4. 📡 CHẠY SEEDER RIÊNG
   - Chia sẻ file nếu không dùng CLI:
     python peer_server.py
   - Nhập đường dẫn file .torrent

5. 📥 CHẠY DOWNLOADER RIÊNG
   - Tải file độc lập từ .torrent:
     python peer_download.py
   - Tự động resume nếu có file dở

IV. 🔁 TÍNH NĂNG RESUME

- Tự lưu tiến trình mỗi piece vào downloads/.progress/
- Nếu quá trình bị ngắt, sẽ tiếp tục từ nơi đã dừng

V. 🌐 TRIỂN KHAI NHIỀU MÁY

- Tracker chạy tại 1 máy cố định (ví dụ: 192.168.1.88)
- Peer nhập IP tracker khi chạy CLI
- Đảm bảo:
  - Cổng 5000 (tracker) mở
  - Cổng 6881 (peer) không bị chặn bởi firewall

────────────────────────────────────────────
✅ Hệ thống hỗ trợ đăng nhập, đa peer, đa file, resume
📡 Kết nối tracker trung tâm, tải file song song từ nhiều peer
✨ Giao diện CLI đơn giản, dễ triển khai trên mạng LAN
