import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unidecode import unidecode
from flask import Flask, request, jsonify
from google.transit import gtfs_realtime_pb2

# =============================================================================
# CONSTANTS & ENV VARIABLES
# =============================================================================

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'False').lower() == 'true'
RUN_GLOBALLY = os.environ.get('RUN_GLOBALLY', 'True').lower() == 'true'
PORT_HTTP_SERVER = int(os.environ.get('PORT_HTTP_SERVER', 5000))

TZ_NAME_CZECHIA = 'Europe/Prague'
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
MAX_DEPARTURE_WINDOW_MINUTES = 120
DEPARTURES_PER_ROUTE_LIMIT = 2

GTFS_RT_URL = 'https://kordis-jmk.cz/gtfs/gtfsReal.dat'
RT_CACHE_TTL_SECONDS = 30

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
DIR_STATIC = 'static'
FILE_DEFAULT = 'index.html'

PARAM_STOP_NAME = 'stop_name'
PARAM_SEARCH_QUERY = 'q'

# =============================================================================
# INITIALIZATION & STATE
# =============================================================================

app = Flask(__name__, static_folder=DIR_STATIC, static_url_path='')
czech_tz = ZoneInfo(TZ_NAME_CZECHIA)

# In-memory cache for GTFS-RT
rt_state = {
    'last_fetch': 0,
    'delays': {} # maps trip_id -> delay in seconds
}

def get_db():
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_rt_delays():
    current_time = time.time()
    if current_time - rt_state['last_fetch'] < RT_CACHE_TTL_SECONDS:
        return rt_state['delays']
        
    try:
        response = requests.get(GTFS_RT_URL, timeout=5)
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        new_delays = {}
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip_id = entity.trip_update.trip.trip_id
                
                # Grab the latest available delay for this trip
                delay_sec = 0
                for stu in entity.trip_update.stop_time_update:
                    if stu.HasField('departure') and stu.departure.delay:
                        delay_sec = stu.departure.delay
                    elif stu.HasField('arrival') and stu.arrival.delay:
                        delay_sec = stu.arrival.delay
                
                new_delays[trip_id] = delay_sec
                
        rt_state['delays'] = new_delays
        rt_state['last_fetch'] = current_time
    except Exception as e:
        print(f"Failed to fetch GTFS-RT: {e}")
        # Keep old data if network fails
        
    return rt_state['delays']

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
    
    # 1. Fetch Realtime Delays
    live_delays = fetch_rt_delays()

    # Added t.trip_id to the query to link with RT data
    query = '''
        SELECT r.route_short_name, r.route_type, r.route_color, r.route_text_color, 
               t.trip_headsign, st.departure_time, s.platform_code, t.trip_id
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s.stop_name = ? AND st.departure_time >= ? AND t.service_id IN ({})
    '''

    for target_date, is_today in [(yesterday, False), (today, True)]:
        services = get_active_services(conn, target_date)
        if not services: continue
        
        # Look back an extra 30 mins just in case a severely delayed bus was scheduled in the past
        search_time_dt = now_dt - timedelta(minutes=30)
        search_time = f'{search_time_dt.hour:02d}:{search_time_dt.minute:02d}:00' if is_today else '24:00:00'
        
        placeholders = ','.join(['?'] * len(services))
        cursor = conn.execute(query.format(placeholders), [stop_name, search_time] + list(services))
        
        for row in cursor.fetchall():
            trip_id = row['trip_id']
            delay_seconds = live_delays.get(trip_id, 0)
            delay_minutes = round(delay_seconds / 60.0)
            
            h, m, _ = map(int, row['departure_time'].split(':'))
            
            # Add delay to absolute minutes
            scheduled_abs_min = (h * MINUTES_PER_HOUR) + m + (0 if not is_today else HOURS_PER_DAY * MINUTES_PER_HOUR)
            real_abs_min = scheduled_abs_min + delay_minutes
            
            all_raw.append({
                'route': row['route_short_name'],
                'type_code': row['route_type'],
                'color': row['route_color'] or DEFAULT_ROUTE_COLOR,
                'text_color': row['route_text_color'] or DEFAULT_TEXT_COLOR,
                'headsign': row['trip_headsign'],
                'platform': row['platform_code'] or 'N/A',
                'real_abs_min': real_abs_min,
                'delay_min': delay_minutes,
                'time': row['departure_time']
            })

    conn.close()
    
    # Sort by the real, delay-adjusted time
    all_raw.sort(key=lambda x: x['real_abs_min'])
    
    final = []
    counts = {}

    for d in all_raw:
        wait = d['real_abs_min'] - curr_abs_min
        
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
                'minutes_left': wait,
                'delay_min': d['delay_min']
            })

    return jsonify(final)

if __name__ == '__main__':
    is_docker = os.environ.get('IS_DOCKER', 'False').lower() == 'true'
    host_addr = '0.0.0.0' if (is_docker or RUN_GLOBALLY) else '127.0.0.1'
    app.run(debug=DEBUG_MODE, host=host_addr, port=PORT_HTTP_SERVER)
