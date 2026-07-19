import os
import sqlite3
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unidecode import unidecode
from flask import Flask, request, jsonify

# =============================================================================
# CONSTANTS & ENV VARIABLES
# =============================================================================

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'False').lower() == 'true'
RUN_GLOBALLY = os.environ.get('RUN_GLOBALLY', 'True').lower() == 'true'
PORT_HTTP_SERVER = int(os.environ.get('PORT_HTTP_SERVER', 5000))
IS_DOCKER = os.environ.get('IS_DOCKER', 'False').lower() == 'true'

TZ_NAME_CZECHIA = 'Europe/Prague'
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
# Expanded for testing
MAX_DEPARTURE_WINDOW_MINUTES = 240 

ROUTE_TYPE_MAP = {
    '0': 'Tram', '1': 'Subway', '2': 'Train', '3': 'Bus',
    '11': 'Trolleybus', '800': 'Trolleybus', '100': 'Rail', '109': 'Suburban Railway'
}
DEFAULT_TRANSIT_TYPE = 'Other'
DEFAULT_ROUTE_COLOR = 'FFFFFF'
DEFAULT_TEXT_COLOR = '000000'

FORMAT_DATE_GTFS = '%Y%m%d'
FORMAT_DAY_NAME = '%A'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_DATA = os.path.join(SCRIPT_DIR, '..', 'data')
PATH_DB = os.path.join(DIR_DATA, 'transit.db')
PATH_LIVE_JSON = os.path.join(DIR_DATA, 'live_delays.json')
DIR_STATIC = 'static'
FILE_DEFAULT = 'index.html'

PARAM_STOP_NAME = 'stop_name'
PARAM_SEARCH_QUERY = 'q'

# =============================================================================
# INITIALIZATION
# =============================================================================

app = Flask(__name__, static_folder=DIR_STATIC, static_url_path='')
czech_tz = ZoneInfo(TZ_NAME_CZECHIA)

def get_db():
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_live_delays():
    if not os.path.exists(PATH_LIVE_JSON):
        if DEBUG_MODE: print(f'DEBUG: {PATH_LIVE_JSON} not found')
        return {}
    try:
        with open(PATH_LIVE_JSON, 'r') as f:
            raw_delays = json.load(f)
            # Normalize keys to match DB block_id
            normalized = {k.lstrip('0'): v for k, v in raw_delays.items()}
            return normalized
    except Exception as e:
        if DEBUG_MODE: print(f'DEBUG: Error reading JSON: {e}')
        return {}

def get_active_services(conn, target_date):
    date_str = target_date.strftime(FORMAT_DATE_GTFS)
    day_name = target_date.strftime(FORMAT_DAY_NAME).lower()
    cursor = conn.execute(f'SELECT service_id FROM calendar WHERE {day_name} = "1" AND start_date <= ? AND end_date >= ?', (date_str, date_str))
    active = set(row['service_id'] for row in cursor.fetchall())
    cursor = conn.execute('SELECT service_id, exception_type FROM calendar_dates WHERE date = ?', (date_str,))
    for row in cursor.fetchall():
        if row['exception_type'] == '1': active.add(row['service_id'])
        elif row['exception_type'] == '2' and row['service_id'] in active: active.remove(row['service_id'])
    return active

@app.route('/')
def index(): return app.send_static_file(FILE_DEFAULT)

@app.route('/api/stops')
def stops():
    q = request.args.get(PARAM_SEARCH_QUERY, '')
    if not q: return jsonify([])
    q_norm = unidecode(q).lower()
    conn = get_db()
    cursor = conn.execute('SELECT DISTINCT stop_name, zone_id FROM stops WHERE stop_name_normalized LIKE ? LIMIT 15', ('%' + q_norm + '%',))
    res = [{'name': row['stop_name'], 'zone': row['zone_id']} for row in cursor.fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/departures')
def departures():
    stop_name = request.args.get(PARAM_STOP_NAME)
    if not stop_name: return jsonify({'error': 'missing stop_name'}), 400

    now_dt = datetime.now(czech_tz)
    today = now_dt.date()
    yesterday = today - timedelta(days=1)
    curr_abs_min = (HOURS_PER_DAY * MINUTES_PER_HOUR) + (now_dt.hour * MINUTES_PER_HOUR) + now_dt.minute

    live_delays = get_live_delays()
    if DEBUG_MODE: print("DEBUG: Live Delays State:", live_delays)
    
    conn = get_db()
    all_raw = []

    # TEST REGIME: Fetching ALL trip and sequence data
    query = '''
        SELECT 
            r.route_short_name, r.route_type, r.route_color, r.route_text_color, r.route_id,
            t.trip_headsign, t.block_id, t.trip_id, t.service_id,
            st.departure_time, st.stop_sequence, s.platform_code, s.stop_id
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s.stop_name = ? AND st.departure_time >= ? AND t.service_id IN ({})
    '''

    for target_date, is_today in [(yesterday, False), (today, True)]:
        services = get_active_services(conn, target_date)
        if not services: continue
        
        search_time_dt = now_dt - timedelta(minutes=30)
        search_time = f'{search_time_dt.hour:02d}:{search_time_dt.minute:02d}:00' if is_today else '24:00:00'
        
        placeholders = ','.join(['?'] * len(services))
        cursor = conn.execute(query.format(placeholders), [stop_name, search_time] + list(services))
        
        for row in cursor.fetchall():
            raw_block_id = str(row['block_id']) if row['block_id'] else ""
            db_block_id = raw_block_id.lstrip('0')
            
            delay_min_raw = live_delays.get(db_block_id)
            has_rt = delay_min_raw is not None
            delay_min = int(float(delay_min_raw)) if has_rt else 0

            h, m, _ = map(int, row['departure_time'].split(':'))
            sch_min = (h * MINUTES_PER_HOUR) + m + (0 if not is_today else HOURS_PER_DAY * MINUTES_PER_HOUR)
            real_abs_min = sch_min + delay_min
            
            all_raw.append({
                'route': row['route_short_name'],
                'route_id': row['route_id'],
                'trip_id': row['trip_id'],
                'service_id': row['service_id'],
                'block_id_raw': raw_block_id,
                'block_id_normalized': db_block_id,
                'type_code': row['route_type'],
                'color': row['route_color'] or DEFAULT_ROUTE_COLOR,
                'text_color': row['route_text_color'] or DEFAULT_TEXT_COLOR,
                'headsign': row['trip_headsign'],
                'platform': row['platform_code'] or 'N/A',
                'stop_id': row['stop_id'],
                'stop_sequence': row['stop_sequence'],
                'scheduled_time': row['departure_time'],
                'real_abs_min': real_abs_min,
                'delay_min': delay_min,
                'has_rt': has_rt
            })

    conn.close()
    all_raw.sort(key=lambda x: x['real_abs_min'])
    
    # In test regime, we return everything found without the route-occurrence limit
    final = []
    for d in all_raw:
        wait = d['real_abs_min'] - curr_abs_min
        if wait < -10 or wait > MAX_DEPARTURE_WINDOW_MINUTES: 
            continue
        
        d['minutes_left'] = wait
        final.append(d)

    return jsonify(final)

if __name__ == '__main__':
    host_addr = '0.0.0.0' if (IS_DOCKER or RUN_GLOBALLY) else '127.0.0.1'
    app.run(debug=DEBUG_MODE, host=host_addr, port=PORT_HTTP_SERVER)
