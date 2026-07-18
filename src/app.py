import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unidecode import unidecode
from flask import Flask, request, jsonify

# =============================================================================
# CONSTANTS
# =============================================================================

# Set to True to allow access from other devices on your network (0.0.0.0)
# Set to False to allow only local access (127.0.0.1)
RUN_GLOBALLY = False
PORT_HTTP_SERVER = 80

# Max time in the future to show departures (2 hours)
MAX_DEPARTURE_WINDOW_MINUTES = 120

# How many departures to show for the same route+headsign+platform combo
DEPARTURES_PER_ROUTE_LIMIT = 2

# =============================================================================
# SYSTEM CONSTANTS
# =============================================================================

TZ_NAME_CZECHIA = 'Europe/Prague'
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60

# Mapping GTFS route_type to human readable strings
ROUTE_TYPE_MAP = {
    '0': 'Tram',
    '1': 'Subway',
    '2': 'Train',
    '3': 'Bus',
    '11': 'Trolleybus',
    '800': 'Trolleybus',
    '100': 'Rail',
    '109': 'Suburban Railway'
}
DEFAULT_TRANSIT_TYPE = 'Other'

# Default colors if missing in GTFS
DEFAULT_ROUTE_COLOR = 'FFFFFF'
DEFAULT_TEXT_COLOR = '000000'

# Formatting
FORMAT_DATE_GTFS = '%Y%m%d'
FORMAT_DAY_NAME = '%A'
FORMAT_ISO_TIME = '%Y-%m-%dT%H:%M:%S'

# Paths
# Points to the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data directory is one level up from the script
DIR_DATA = os.path.join(SCRIPT_DIR, '..', 'data')
# Full path to the database file
PATH_DB = os.path.join(DIR_DATA, 'transit.db')
# Folder containing static assets
DIR_STATIC = 'static'
# The default file to serve for the root path
FILE_DEFAULT = 'index.html'

# API Parameter Keys
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
def index():
    # Serves index.html at the root path without index.html appearing in the URL
    return app.send_static_file(FILE_DEFAULT)

@app.route('/api/stops')
def stops():
    q = request.args.get(PARAM_SEARCH_QUERY, '')
    if not q: return jsonify([])
    q_norm = unidecode(q).lower()
    conn = get_db()
    cursor = conn.execute(
        'SELECT DISTINCT stop_name, zone_id FROM stops WHERE stop_name_normalized LIKE ? LIMIT 15', 
        ('%' + q_norm + '%',)
    )
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

    conn = get_db()
    all_raw = []

    query = '''
        SELECT r.route_short_name, r.route_type, r.route_color, r.route_text_color, 
               t.trip_headsign, st.departure_time, s.platform_code
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s.stop_name = ? AND st.departure_time >= ? AND t.service_id IN ({})
    '''

    for target_date, is_today in [(yesterday, False), (today, True)]:
        services = get_active_services(conn, target_date)
        if not services: continue
        
        search_time = f'{now_dt.hour:02d}:{now_dt.minute:02d}:00' if is_today else '24:00:00'
        placeholders = ','.join(['?'] * len(services))
        cursor = conn.execute(query.format(placeholders), [stop_name, search_time] + list(services))
        
        for row in cursor.fetchall():
            h, m, _ = map(int, row['departure_time'].split(':'))
            abs_min = (h * MINUTES_PER_HOUR) + m + (0 if not is_today else HOURS_PER_DAY * MINUTES_PER_HOUR)
            
            all_raw.append({
                'route': row['route_short_name'],
                'type_code': row['route_type'],
                'color': row['route_color'] or DEFAULT_ROUTE_COLOR,
                'text_color': row['route_text_color'] or DEFAULT_TEXT_COLOR,
                'headsign': row['trip_headsign'],
                'platform': row['platform_code'] or 'N/A',
                'abs_min': abs_min,
                'time': row['departure_time']
            })

    conn.close()
    all_raw.sort(key=lambda x: x['abs_min'])
    
    final = []
    counts = {}

    for d in all_raw:
        wait = d['abs_min'] - curr_abs_min
        if wait < 0 or wait > MAX_DEPARTURE_WINDOW_MINUTES: continue
        
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
                'minutes_left': wait
            })

    return jsonify(final)

if __name__ == '__main__':
    if (os.environ.get('IS_DOCKER', 'False').lower() == 'true'): RUN_GLOBALLY = True

    host_addr = '0.0.0.0' if RUN_GLOBALLY else '127.0.0.1'
    app.run(debug=False, host=host_addr, port=PORT_HTTP_SERVER)
