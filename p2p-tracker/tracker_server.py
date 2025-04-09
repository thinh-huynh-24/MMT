
from flask import Flask, request, jsonify
from collections import defaultdict

app = Flask(__name__)
torrents = defaultdict(list)

@app.route('/announce', methods=['POST'])
def announce():
    data = request.json
    info_hash = data['info_hash']
    peer = {
        'peer_id': data['peer_id'],
        'ip': data['ip'],
        'port': data['port']
    }
    event = data['event']
    if event == 'started':
        if peer not in torrents[info_hash]:
            torrents[info_hash].append(peer)
        return jsonify({'status': 'registered', 'peers': torrents[info_hash]})
    elif event == 'stopped':
        if peer in torrents[info_hash]:
            torrents[info_hash].remove(peer)
        return jsonify({'status': 'removed'})
    return jsonify({'status': 'ignored'})

@app.route('/peers', methods=['GET'])
def get_peers():
    info_hash = request.args.get('info_hash')
    return jsonify({'info_hash': info_hash, 'peers': torrents.get(info_hash, [])})

if __name__ == '__main__':
    # Cho phép các máy khác trong LAN truy cập tracker
    app.run(host='0.0.0.0', port=5000)
