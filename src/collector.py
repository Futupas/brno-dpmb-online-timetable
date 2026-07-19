import websocket
import json
import os
import threading
import time

# =============================================================================
# CONSTANTS
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
PATH_JSON_OUT = os.path.join(DATA_DIR, 'live_delays.json')
WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe'
DISK_SAVE_INTERVAL = 5

# =============================================================================
# STATE
# =============================================================================
# Map of { vehicle_id: { delay, last_stop, final_stop, line_id, wkid } }
live_data_map = {}
map_lock = threading.Lock()

# =============================================================================
# LOGIC
# =============================================================================

def save_to_disk():
    '''Periodically saves the entire live_data_map to disk.'''
    while True:
        with map_lock:
            if live_data_map:
                try:
                    temp_file = PATH_JSON_OUT + '.tmp'
                    with open(temp_file, 'w') as f:
                        json.dump(live_data_map, f)
                    os.replace(temp_file, PATH_JSON_OUT)
                except Exception as e:
                    print(f'Disk Save Error: {e}')
        time.sleep(DISK_SAVE_INTERVAL)

def on_message(ws, message):
    try:
        data = json.loads(message)
        attr = data.get('attributes', {})
        geom = data.get('geometry', {})
        
        v_id = attr.get('ID')
        if v_id is None:
            return

        # Extract all requested extra data
        payload = {
            'delay': float(attr.get('Delay', 0)),
            'updated_at': attr.get('TimeUpdated', 0) / 1000.0,  # Convert ms to seconds
            # 'last_stop': attr.get('LastStopID'),
            # 'final_stop': attr.get('FinalStopID'),
            # 'line_id': attr.get('LineID'),
            'wkid': geom.get('spatialReference', {}).get('wkid')
        }

        with map_lock:
            # Overwrite existing entry. 0 is stored as 0, not deleted.
            live_data_map[str(v_id)] = payload

    except Exception as e:
        print(f'Parse Error: {e}')

def run_ws():
    ws = websocket.WebSocketApp(
        WS_URL, 
        on_message=on_message, 
        on_error=lambda w, e: print(f'WS Error: {e}'),
        on_close=lambda w, s, m: (print('### WS Closed. Reconnecting... ###'), time.sleep(5), run_ws())
    )
    ws.run_forever(ping_interval=30)

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Load existing state if available
    if os.path.exists(PATH_JSON_OUT):
        try:
            with open(PATH_JSON_OUT, 'r') as f:
                live_data_map = json.load(f)
                print(f'Restored {len(live_data_map)} vehicles from disk.')
        except:
            print('Could not restore existing state.')

    threading.Thread(target=save_to_disk, daemon=True).start()
    print(f'Collector active. Connecting to {WS_URL}')
    run_ws()
