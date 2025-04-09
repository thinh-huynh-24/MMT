# peer_client.py
import requests

class PeerClient:
    def __init__(self, tracker_url, info_hash, peer_id, ip, port):
        self.tracker_url = tracker_url
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.ip = ip
        self.port = port

    def announce(self, event):
        url = f"{self.tracker_url}/announce"
        data = {
            "info_hash": self.info_hash,
            "peer_id": self.peer_id,
            "ip": self.ip,
            "port": self.port,
            "event": event
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_peers(self):
        url = f"{self.tracker_url}/peers"
        try:
            response = requests.get(url, params={"info_hash": self.info_hash})
            return response.json()
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    # THÔNG TIN PEER GIẢ LẬP
    peer = PeerClient(
        tracker_url="http://localhost:5000",
        info_hash="abc123",
        peer_id="peer001",
        ip="127.0.0.1",
        port=6881
    )

    print("📤 Gửi STARTED (đăng ký peer với tracker)...")
    result1 = peer.announce("started")
    print(result1)

    print("\n🔍 Truy vấn danh sách các peers đang chia sẻ file...")
    result2 = peer.get_peers()
    print(result2)

    print("\n❌ Gửi STOPPED (peer thoát mạng)...")
    result3 = peer.announce("stopped")
    print(result3)
