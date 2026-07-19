import websocket
import json
import sqlite3
import os
import threading
import time

# =============================================================================
# CONSTANTS
# =============================================================================

VERBOSE = True

# --- Path Constants ---
# Directory where this script is located.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Shared data directory for DB and JSON output.
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
# Path to the SQLite database for name lookups.
PATH_DB = os.path.join(DATA_DIR, 'transit.db')
# Output file for the Flask app to read.
PATH_JSON_OUT = os.path.join(DATA_DIR, 'live_delays.json')

# --- IDS JMK ID Mapping Constants ---
# Prefix used for routes in the Brno GTFS dataset.
PREFIX_ROUTE = 'L'
# Prefix used for stops in the Brno GTFS dataset.
PREFIX_STOP = 'U'

# --- WebSocket Constants ---
# The live StreamServer URL for Kordis transit data.
WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe'
# Interval in seconds for saving the memory map to disk.
DISK_SAVE_INTERVAL = 5
# Timeout for the WebSocket connection.
WS_TIMEOUT = 10
# Interval for sending keep-alive pings.
WS_PING_INTERVAL = 30

# =============================================================================
# STATE & HELPERS
# =============================================================================

# Global dictionary to store {course: delay_min}.
delay_map = {}
map_lock = threading.Lock()

def get_transit_info(line_id, last_stop_id, final_stop_id):
    '''Fetches human-readable names for the route and stops from the database.'''
    if not os.path.exists(PATH_DB):
        return None, None, None
    try:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        
        # We use partial matching because WebSocket IDs are often subsets of GTFS IDs.
        query = '''
            SELECT 
                (SELECT route_short_name FROM routes WHERE route_id LIKE 'L%' || ? || '%' LIMIT 1) as route_name,
                (SELECT stop_name FROM stops WHERE stop_id LIKE 'U' || ? || '%' LIMIT 1) as last_stop_name,
                (SELECT stop_name FROM stops WHERE stop_id LIKE 'U' || ? || '%' LIMIT 1) as final_stop_name
        '''
        res = conn.execute(query, (str(line_id), str(last_stop_id), str(final_stop_id))).fetchone()
        conn.close()
        
        if res:
            return res['last_stop_name'], res['route_name'], res['final_stop_name']
    except:
        pass
    return None, None, None

def save_to_disk():
    '''Periodically saves the live delay state to a JSON file.'''
    while True:
        with map_lock:
            if delay_map:
                try:
                    temp_file = PATH_JSON_OUT + '.tmp'
                    with open(temp_file, 'w') as f:
                        json.dump(delay_map, f)
                    os.replace(temp_file, PATH_JSON_OUT)
                except Exception as e:
                    print('Disk Save Error: ' + str(e))
        time.sleep(DISK_SAVE_INTERVAL)

# =============================================================================
# WEBSOCKET HANDLERS
# =============================================================================

def on_message(ws, message):
    try:
        data = json.loads(message)
        attr = data.get('attributes', {})
        
        course = attr.get('Course')
        delay = attr.get('Delay')
        line_id = attr.get('LineID')
        last_stop_id = attr.get('LastStopID')
        final_stop_id = attr.get('FinalStopID')

        if course is not None and delay is not None:
            with map_lock:
                delay_map[str(course)] = float(delay)

            # --- TESTING LINE ---
            # Resolves IDs to names and prints the vehicle status to the console.
            stop, route, destination, delay_val = *get_transit_info(line_id, last_stop_id, final_stop_id), delay
            if VERBOSE and stop and route and destination and delay_val > 0:
                print(f'Stop: {stop}, Route: {route}, Destination: {destination}, Delay: {delay_val}min')

    except Exception as e:
        print('Parse Error: ' + str(e))

def on_error(ws, error):
    print('WebSocket Error: ' + str(error))

def on_close(ws, status, msg):
    print(f'### WS Closed ({status}): {msg}. Reconnecting... ###')
    time.sleep(5)
    run_ws()

def on_open(ws):
    print('### WebSocket Connection Opened ###')

def run_ws():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=WS_PING_INTERVAL, ping_timeout=WS_TIMEOUT)

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    threading.Thread(target=save_to_disk, daemon=True).start()
    run_ws()
