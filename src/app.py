import os
import sqlite3
import json
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unidecode import unidecode
from flask import Flask, request, jsonify
from google.transit import gtfs_realtime_pb2
from ingest import ingest
import time

# =============================================================================
# CONSTANTS & ENV
# =============================================================================
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'True').lower() == 'true'
RUN_GLOBALLY = os.environ.get('RUN_GLOBALLY', 'False').lower() == 'true'
PORT_HTTP_SERVER = int(os.environ.get('PORT_HTTP_SERVER', 5000))
IS_DOCKER = os.environ.get('IS_DOCKER', 'False').lower() == 'true'

TZ_NAME_CZECHIA = 'Europe/Prague'
HOURS_PER_DAY, MINUTES_PER_HOUR = 24, 60
MAX_DEPARTURE_WINDOW_MINUTES = 120
DEPARTURES_PER_ROUTE_LIMIT = 2

GTFS_RT_BINARY_URL = 'https://kordis-jmk.cz/gtfs/gtfsReal.dat'
RT_BINARY_CACHE_TTL = 30

# Maximum age of real-time data before it's considered "stale" (10 minutes)
MAX_RT_AGE_SECONDS = 60 * 10

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_DATA = os.path.join(SCRIPT_DIR, '..', 'data')
PATH_DB = os.path.join(DIR_DATA, 'transit.db')
PATH_WS_JSON = os.path.join(DIR_DATA, 'live_delays.json')

app = Flask(__name__, static_folder='static', static_url_path='')
czech_tz = ZoneInfo(TZ_NAME_CZECHIA)

# Cache for the GTFS-RT Binary join (trip_id -> vehicle_label)
binary_cache = {'last_fetch': 0, 'mapping': {}}

# =============================================================================
# LOGIC
# =============================================================================

def get_trip_to_label_map():
    '''Fetches GTFS-RT binary to map TripIDs to Vehicle Labels (WebSocket IDs).'''
    now = time.time()
    if now - binary_cache['last_fetch'] < RT_BINARY_CACHE_TTL:
        return binary_cache['mapping']
    
    try:
        res = requests.get(GTFS_RT_BINARY_URL, timeout=5)
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(res.content)
        
        new_map = {}
        for entity in feed.entity:
            if entity.HasField('vehicle'):
                t_id = entity.vehicle.trip.trip_id
                v_label = entity.vehicle.vehicle.label # The "label" is the WS "ID"
                if t_id and v_label:
                    new_map[str(t_id)] = str(v_label)
        
        binary_cache['mapping'] = new_map
        binary_cache['last_fetch'] = now
    except Exception as e:
        if DEBUG_MODE: print(f'Binary RT Fetch Error: {e}')
    
    return binary_cache['mapping']

def get_ws_delays():
    if not os.path.exists(PATH_WS_JSON): return {}
    try:
        with open(PATH_WS_JSON, 'r') as f: 
            return json.load(f) # Returns { "v_id": { "delay": X, ... } }
    except: return {}

def get_active_services(conn, date_obj):
    ds = date_obj.strftime('%Y%m%d')
    dn = date_obj.strftime('%A').lower()
    cursor = conn.execute(f'SELECT service_id FROM calendar WHERE {dn}="1" AND start_date<=? AND end_date>=?', (ds, ds))
    active = set(row['service_id'] for row in cursor.fetchall())
    cursor = conn.execute('SELECT service_id, exception_type FROM calendar_dates WHERE date=?', (ds,))
    for row in cursor.fetchall():
        if row['exception_type'] == '1': active.add(row['service_id'])
        elif row['exception_type'] == '2' and row['service_id'] in active: active.remove(row['service_id'])
    return active

@app.route('/')
def index(): return app.send_static_file('index.html')

@app.route('/api/stops')
def stops():
    q = request.args.get('q', '')
    if not q: return jsonify([])
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('SELECT DISTINCT stop_name, zone_id FROM stops WHERE stop_name_normalized LIKE ? LIMIT 15', ('%' + unidecode(q).lower() + '%',))
    res = [{'name': r['stop_name'], 'zone': r['zone_id']} for r in cursor.fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/departures')
def departures():
    stop_name = request.args.get('stop_name')
    if not stop_name: return jsonify({'error': 'missing stop_name'}), 400

    now_dt = datetime.now(czech_tz)
    curr_min = (HOURS_PER_DAY * MINUTES_PER_HOUR) + (now_dt.hour * MINUTES_PER_HOUR) + now_dt.minute

    # 1. Get cross-reference maps
    trip_to_label = get_trip_to_label_map()
    label_to_delay = get_ws_delays()
    
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    all_raw = []

    query = '''
        SELECT r.route_short_name, r.route_type, r.route_color, r.route_text_color, 
               t.trip_headsign, t.trip_id, st.departure_time, s.platform_code
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s.stop_name = ? AND st.departure_time >= ? AND t.service_id IN ({})
    '''

    for target_date, is_today in [(now_dt.date() - timedelta(days=1), False), (now_dt.date(), True)]:
        services = get_active_services(conn, target_date)
        if not services: continue
        search_time = f'{(now_dt - timedelta(minutes=30)).hour:02d}:{now_dt.minute:02d}:00' if is_today else '24:00:00'
        placeholders = ','.join(['?'] * len(services))
        cursor = conn.execute(query.format(placeholders), [stop_name, search_time] + list(services))
        
        for row in cursor.fetchall():
            # JOIN STAGE: TripID -> Label -> Delay
            trip_id = str(row['trip_id'])
            v_label = trip_to_label.get(trip_id)
            
            # Access the nested 'delay' key
            v_data = label_to_delay.get(v_label) if v_label else None
            delay_min = 0
            has_rt = False

            if v_data:
                # Calculate how many seconds ago this vehicle was updated
                age = time.time() - v_data.get('updated_at', 0)
                
                if age < MAX_RT_AGE_SECONDS:
                    delay_min = int(v_data['delay'])
                    has_rt = True
                elif DEBUG_MODE:
                    print(f"DEBUG: Ignoring stale RT data for {v_label} (Age: {round(age)}s)")

            h, m, _ = map(int, row['departure_time'].split(':'))
            sch_min = (h * MINUTES_PER_HOUR) + m + (0 if not is_today else HOURS_PER_DAY * MINUTES_PER_HOUR)
            real_min = sch_min + delay_min
            
            all_raw.append({
                'route': row['route_short_name'], 'type_code': row['route_type'],
                'color': row['route_color'] or 'FFFFFF', 'text_color': row['route_text_color'] or '000000',
                'headsign': row['trip_headsign'], 'platform': row['platform_code'] or 'N/A',
                'real_abs_min': real_min, 'delay_min': delay_min, 'has_rt': has_rt
            })

    conn.close()
    all_raw.sort(key=lambda x: x['real_abs_min'])
    
    final, counts = [], {}
    for d in all_raw:
        # Calculate wait time: (Schedule + Delay) - Now
        wait = d['real_abs_min'] - curr_min
        
        # Eliminate trips that have already departed (wait < 0)
        # Also ignore trips beyond the 2-hour window
        if wait < 0 or wait > MAX_DEPARTURE_WINDOW_MINUTES: 
            continue
        
        key = (d['platform'], d['route'], d['headsign'])
        counts[key] = counts.get(key, 0) + 1
        
        if counts[key] <= DEPARTURES_PER_ROUTE_LIMIT:
            final.append({
                'platform': d['platform'],
                'route': d['route'],
                'type_code': d['type_code'],
                'color': d['color'],
                'text_color': d['text_color'],
                'headsign': d['headsign'],
                'minutes_left': wait, # This will always be >= 0 now
                'delay_min': d['delay_min'],
                'has_rt': d['has_rt']
            })

    return jsonify(final)

if __name__ == '__main__':
    if not os.path.exists(PATH_DB):
        print('Database not found. Starting automatic ingestion...')
        ingest()
    host = '0.0.0.0' if (IS_DOCKER or RUN_GLOBALLY) else '127.0.0.1'
    app.run(debug=DEBUG_MODE, host=host, port=PORT_HTTP_SERVER)
