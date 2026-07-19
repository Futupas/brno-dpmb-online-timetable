import websocket
import json
import sqlite3
import os

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'transit.db')
WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe'

def get_names(line_id, stop_id):
    if not os.path.exists(DB_PATH):
        return None, None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Based on your DB dump:
        # Route: Feed '4' -> DB 'L104D99'. We search for route_id LIKE 'L%' || ? || '%'
        # Stop: Feed '1371' -> DB 'U1371Z...'. We search for stop_id LIKE 'U' || ? || '%'
        
        query = '''
            SELECT 
                (SELECT route_short_name FROM routes WHERE route_id LIKE 'L%' || ? || '%' LIMIT 1) as route_name,
                (SELECT stop_name FROM stops WHERE stop_id LIKE 'U' || ? || '%' LIMIT 1) as stop_name
        '''
        res = conn.execute(query, (str(line_id), str(stop_id))).fetchone()
        conn.close()
        
        if res:
            return res['route_name'], res['stop_name']
    except Exception:
        pass
    return None, None

def on_message(ws, message):
    try:
        data = json.loads(message)
        attr = data.get('attributes', {})
        
        delay = attr.get('Delay')
        line_id = attr.get('LineID')
        stop_id = attr.get('LastStopID')

        # Only print to console if it's delayed and we have the IDs
        if delay is not None and delay > 0 and line_id and stop_id:
            route_name, stop_name = get_names(line_id, stop_id)
            if route_name and stop_name:
                print(f'bus {route_name} near {stop_name} is delayed by {delay}min')
    except Exception as e:
        pass

def on_error(ws, error):
    print(f'WS Error: {error}')

def on_close(ws, status, msg):
    print('### Connection Closed ###')

def on_open(ws):
    print('### Connection Opened ###')

if __name__ == '__main__':
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
