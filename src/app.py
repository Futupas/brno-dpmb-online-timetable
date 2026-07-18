import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unidecode import unidecode
from flask import Flask, request, jsonify

# =============================================================================
# CONSTANTS
# =============================================================================

TZ_NAME_CZECHIA = 'Europe/Prague'
PORT_HTTP_SERVER = 5000
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60

# How many departures to show for the same route+headsign+platform combo
DEPARTURES_PER_ROUTE_LIMIT = 2

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

# Formatting
FORMAT_DATE_GTFS = '%Y%m%d'
FORMAT_DAY_NAME = '%A'
FORMAT_ISO_TIME = '%Y-%m-%dT%H:%M:%S'

# Paths
DIR_PARENT = '..'
DIR_DATA = 'data'
FILE_DB_NAME = 'transit.db'
DIR_STATIC = 'static'

# API Keys
PARAM_STOP_NAME = 'stop_name'
PARAM_SEARCH_QUERY = 'q'

# =============================================================================
# INITIALIZATION
# =============================================================================

app = Flask(__name__, static_folder=DIR_STATIC, static_url_path='')
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, DIR_PARENT, DIR_DATA, FILE_DB_NAME)
czech_tz = ZoneInfo(TZ_NAME_CZECHIA)

def get_db():
    conn = sqlite3.connect(db_path)
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

@app.route('/api/time')
def get_server_time():
    now = datetime.now(czech_tz)
    return jsonify({
        'iso': now.strftime(FORMAT_ISO_TIME),
        'timestamp': int(now.timestamp()),
        'timezone': TZ_NAME_CZECHIA
    })

@app.route('/api/stops')
def stops():
    q = request.args.get(PARAM_SEARCH_QUERY, '')
    if not q: return jsonify([])
    q_norm = unidecode(q).lower()
    conn = get_db()
    cursor = conn.execute('SELECT DISTINCT stop_name FROM stops WHERE stop_name_normalized LIKE ? LIMIT 15', ('%' + q_norm + '%',))
    res = [row['stop_name'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/departures')
def departures():
    stop_name = request.args.get(PARAM_STOP_NAME)
    if not stop_name: return jsonify({'error': 'missing stop_name'}), 400

    now_dt = datetime.now(czech_tz)
    today = now_dt.date()
    yesterday = today - timedelta(days=1)
    
    # Epoch: minutes from yesterday midnight
    curr_abs_min = (HOURS_PER_DAY * MINUTES_PER_HOUR) + (now_dt.hour * MINUTES_PER_HOUR) + now_dt.minute

    conn = get_db()
    all_raw = []

    # SQL structure
    query = '''
        SELECT r.route_short_name, r.route_type, t.trip_headsign, st.departure_time, s.platform_code
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s.stop_name = ? AND st.departure_time >= ? AND t.service_id IN ({})
    '''

    # Fetch Yesterday (rollover) and Today
    for target_date, is_today in [(yesterday, False), (today, True)]:
        services = get_active_services(conn, target_date)
        if not services: continue
        
        # If yesterday, we look for times >= 24:00. If today, we look for times >= current.
        search_time = f'{now_dt.hour:02d}:{now_dt.minute:02d}:00' if is_today else '24:00:00'
        
        placeholders = ','.join(['?'] * len(services))
        cursor = conn.execute(query.format(placeholders), [stop_name, search_time] + list(services))
        
        for row in cursor.fetchall():
            h, m, _ = map(int, row['departure_time'].split(':'))
            # Absolute minutes calculation
            abs_min = (h * MINUTES_PER_HOUR) + m + (0 if not is_today else HOURS_PER_DAY * MINUTES_PER_HOUR)
            
            all_raw.append({
                'route': row['route_short_name'],
                'type': ROUTE_TYPE_MAP.get(row['route_type'], DEFAULT_TRANSIT_TYPE),
                'headsign': row['trip_headsign'],
                'platform': row['platform_code'] or 'N/A',
                'abs_min': abs_min,
                'time': row['departure_time']
            })

    conn.close()
    
    # Sort by time
    all_raw.sort(key=lambda x: x['abs_min'])
    
    final = []
    counts = {} # Tracks (platform, route, headsign) occurrences

    for d in all_raw:
        wait = d['abs_min'] - curr_abs_min
        if wait < 0: continue
        
        key = (d['platform'], d['route'], d['headsign'])
        counts[key] = counts.get(key, 0) + 1
        
        if counts[key] <= DEPARTURES_PER_ROUTE_LIMIT:
            final.append({
                'platform': d['platform'],
                'route': d['route'],
                'type': d['type'],
                'headsign': d['headsign'],
                'minutes_left': wait,
                'time': d['time']
            })

    return jsonify(final)

if __name__ == '__main__':
    app.run(debug=True, port=PORT_HTTP_SERVER)
