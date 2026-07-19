import websocket
import json
import sqlite3
import os
import threading
import time

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
PATH_DB = os.path.join(DATA_DIR, 'transit.db')
PATH_JSON_OUT = os.path.join(DATA_DIR, 'live_delays.json')
WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe'
DISK_SAVE_INTERVAL = 5

# Global dictionary to store {course: delay_min}
delay_map = {}
map_lock = threading.Lock()

def get_transit_info(line_id, last_stop_id, final_stop_id):
    if not os.path.exists(PATH_DB): return None, None, None
    try:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        query = '''
            SELECT 
                (SELECT route_short_name FROM routes WHERE route_id LIKE 'L%' || ? || '%' LIMIT 1) as route_name,
                (SELECT stop_name FROM stops WHERE stop_id LIKE 'U' || ? || '%' LIMIT 1) as last_stop_name,
                (SELECT stop_name FROM stops WHERE stop_id LIKE 'U' || ? || '%' LIMIT 1) as final_stop_name
        '''
        res = conn.execute(query, (str(line_id), str(last_stop_id), str(final_stop_id))).fetchone()
        conn.close()
        if res: return res['last_stop_name'], res['route_name'], res['final_stop_name']
    except: pass
    return None, None, None

def save_to_disk():
    while True:
        with map_lock:
            try:
                temp_file = PATH_JSON_OUT + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(delay_map, f)
                os.replace(temp_file, PATH_JSON_OUT)
            except Exception as e:
                print(f'Disk Save Error: {e}')
        time.sleep(DISK_SAVE_INTERVAL)

def on_message(ws, message):
    try:
        data = json.loads(message)
        attr = data.get('attributes', {})

        # if attr.get('VType') == 0: return # This is not a passenger ride: https://data.brno.cz/datasets/mestobrno::polohy-vozidel-hromadn%C3%A9-dopravy-public-transit-positional-data/about

        if attr.get('VType') != 0: return # temporary


        print('message starts')
        # print(data.get('geometry'))
        # print(data.get('attributes'))
        print(message)
        print('message ends')
        print()
        return

        course = attr.get('Course')
        delay = attr.get('Delay')
        
        if course is not None and delay is not None:
            course_str = str(course)
            with map_lock:
                if delay == 0:
                    # Remove the delay entry if it's explicitly 0 (reset)
                    delay_map.pop(course_str, None)
                else:
                    # Update or Add the delay
                    delay_map[course_str] = float(delay)

            if delay > 0:
                s, r, d = get_transit_info(attr.get('LineID'), attr.get('LastStopID'), attr.get('FinalStopID'))
                if s: print(f'Stop: {s}, Route: {r}, Destination: {d}, Delay: {delay}min, attrs: {attr}\n')
    except Exception as e:
        print(f'Parse Error: {e}')

def on_error(ws, error): print(f'WebSocket Error: {error}')
def on_close(ws, status, msg):
    print(f'### WS Closed ({status}). Reconnecting... ###')
    time.sleep(5)
    run_ws()

def run_ws():
    ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever(ping_interval=30, ping_timeout=10)

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # --- Persistence: Load existing delays into memory on startup ---
    if os.path.exists(PATH_JSON_OUT):
        try:
            with open(PATH_JSON_OUT, 'r') as f:
                delay_map = json.load(f)
                print(f'Initial load: {len(delay_map)} delays restored from disk.')
        except:
            print('Could not load existing delays file.')

    threading.Thread(target=save_to_disk, daemon=True).start()
    run_ws()
