from flask import Flask, request, jsonify
from collections import defaultdict
import json
import os

app = Flask(__name__)

# File lưu trữ dữ liệu tạm
DATA_FILE = "torrents_data.json"

# Load dữ liệu torrents từ file
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Ghi dữ liệu torrents vào file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Khởi tạo dữ liệu
torrents = load_data()

@app.route('/')
def index():
    return jsonify({"message": "Tracker server is running!"})

@app.route('/announce', methods=['POST'])
def announce():
    data = request.json
    required_fields = {'info_hash', 'peer_id', 'ip', 'port', 'event'}
    if not required_fields.issubset(data):
        return jsonify({'error': 'Missing fields'}), 400

    info_hash = data['info_hash']
    peer = {
        'peer_id': data['peer_id'],
        'ip': data['ip'],
        'port': data['port']
    }

    # Khởi tạo danh sách peer cho info_hash nếu chưa có
    if info_hash not in torrents:
        torrents[info_hash] = []

    if data['event'] == 'started':
        if peer not in torrents[info_hash]:
            torrents[info_hash].append(peer)
        save_data(torrents)
        return jsonify({'status': 'peer registered', 'peers': torrents[info_hash]})

    elif data['event'] == 'completed':
        return jsonify({'status': 'completed acknowledged'})

    elif data['event'] == 'stopped':
        if peer in torrents[info_hash]:
            torrents[info_hash].remove(peer)
        save_data(torrents)
        return jsonify({'status': 'peer removed'})

    return jsonify({'error': 'Invalid event'}), 400

@app.route('/peers', methods=['GET'])
def get_peers():
    info_hash = request.args.get('info_hash')
    if not info_hash:
        return jsonify({'error': 'Missing info_hash'}), 400

    peer_list = torrents.get(info_hash, [])
    return jsonify({'info_hash': info_hash, 'peers': peer_list})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
