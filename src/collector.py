import websocket
import json
import os
import threading
import time

# --- Configuration ---
# Represents the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Shared data directory
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
# Output file for the Flask app to read
JSON_OUT = os.path.join(DATA_DIR, 'live_delays.json')
# The WebSocket URL provided by Brno/Kordis
WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe'
# Time in seconds between saving the state to disk
SAVE_INTERVAL = 5

# Thread-safe dictionary to store {course: delay_min}
delay_map = {}
map_lock = threading.Lock()

def save_to_disk():
    '''Periodically dumps the memory map to a JSON file for the API to read.'''
    while True:
        with map_lock:
            if delay_map:
                try:
                    temp_file = JSON_OUT + '.tmp'
                    with open(temp_file, 'w') as f:
                        json.dump(delay_map, f)
                    # Atomic rename to prevent the Flask app from reading a half-written file
                    os.replace(temp_file, JSON_OUT)
                except Exception as e:
                    print(f'Disk Save Error: {e}')
        time.sleep(SAVE_INTERVAL)

def on_message(ws, message):
    try:
        data = json.loads(message)
        attr = data.get('attributes', {})
        
        # 'Course' in the live feed maps to 'block_id' in GTFS trips.txt
        course = attr.get('Course')
        delay = attr.get('Delay')

        if course is not None and delay is not None:
            with map_lock:
                # We store everything as strings to match GTFS block_ids
                delay_map[str(course)] = float(delay)
    except Exception as e:
        print(f'Parse Error: {e}')

def on_error(ws, error):
    print(f'WebSocket Error: {error}')

def on_close(ws, status, msg):
    print(f'### WS Closed ({status}): {msg}. Reconnecting... ###')
    time.sleep(5)
    run_ws()

def run_ws():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    # Ping keeps the connection alive through university/corporate firewalls
    ws.run_forever(ping_interval=30, ping_timeout=10)

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    threading.Thread(target=save_to_disk, daemon=True).start()
    print(f'Collector started. Connecting to {WS_URL}...')
    run_ws()
