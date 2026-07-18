import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unidecode import unidecode
from flask import Flask, request, jsonify

# =============================================================================
# CONSTANTS
# =============================================================================

# --- Time and Timezone Constants ---
# Strictly enforce local time for Brno, Czechia as requested.
TZ_NAME_CZECHIA = 'Europe/Prague'
# Number of hours in a standard day, used to calculate yesterday's GTFS times.
HOURS_PER_DAY = 24
# Number of minutes in an hour, used for converting timestamps into total minutes.
MINUTES_PER_HOUR = 60
# Number of days to subtract to get yesterday's date.
DAYS_YESTERDAY_OFFSET = 1
# Default seconds string for building GTFS time query strings.
SECONDS_ZERO_PADDED = '00'

# --- Formatting Constants ---
# GTFS calendar.txt dates are formatted as YYYYMMDD.
FORMAT_DATE_GTFS = '%Y%m%d'
# Used to get the lower-case weekday name (e.g., 'monday') for calendar.txt columns.
FORMAT_DAY_NAME = '%A'
# Used to split the GTFS departure time string into components.
STR_TIME_SPLIT_CHAR = ':'
# Index of the hour component after splitting the time string.
IDX_TIME_HOUR = 0
# Index of the minute component after splitting the time string.
IDX_TIME_MINUTE = 1

# --- Database & File Path Constants ---
# Represents the parent directory relative to this script.
DIR_PARENT = '..'
# The directory where the transit files are stored.
DIR_DATA = 'data'
# The name of the SQLite database file.
FILE_DB_NAME = 'transit.db'
# The name of the folder containing static frontend files.
DIR_STATIC = 'static'
# The default file to serve on the root route.
FILE_INDEX = 'index.html'

# --- Server Constants ---
# The HTTP port the Flask server will listen on.
PORT_HTTP_SERVER = 5000

# --- API Route Constants ---
# The root endpoint for the frontend.
ROUTE_ROOT = '/'
# The API endpoint to search for stops.
ROUTE_API_STOPS = '/api/stops'
# The API endpoint to get departures for a stop.
ROUTE_API_DEPARTURES = '/api/departures'

# --- API Parameter & Response Constants ---
# The query parameter used for searching stops.
PARAM_SEARCH_QUERY = 'q'
# The query parameter specifying the stop name for departures.
PARAM_STOP_NAME = 'stop_name'
# The JSON key used for returning error messages.
JSON_KEY_ERROR = 'error'
# The error message returned when a stop name is omitted.
MSG_ERR_MISSING_STOP = 'stop_name required'
# The HTTP status code for a bad request (client error).
HTTP_STATUS_BAD_REQUEST = 400

# --- Database Query Constants ---
# The SQL wildcard character for LIKE queries.
SQL_WILDCARD = '%'
# The maximum number of stops to return in the search dropdown to prevent UI lag.
LIMIT_SEARCH_STOPS = 15
# The maximum number of database rows to fetch per day query to bound memory usage.
LIMIT_DEPARTURES_DB = 300
# The GTFS string value indicating a service is active on a given day.
GTFS_VAL_ACTIVE = '1'
# The GTFS exception_type value indicating a service is added for a specific date.
GTFS_EXCEPTION_ADDED = '1'
# The GTFS exception_type value indicating a service is removed for a specific date.
GTFS_EXCEPTION_REMOVED = '2'

# --- Default Fallback Constants ---
# The default string to display if a stop has no platform code assigned.
DEFAULT_PLATFORM_CODE = 'N/A'


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
    """Fetches active service_ids for a specific date using calendar and calendar_dates."""
    date_str = target_date.strftime(FORMAT_DATE_GTFS)
    day_name = target_date.strftime(FORMAT_DAY_NAME).lower()

    calendar_query = f'''
        SELECT service_id FROM calendar 
        WHERE {day_name} = ? AND start_date <= ? AND end_date >= ?
    '''
    cursor = conn.execute(calendar_query, (GTFS_VAL_ACTIVE, date_str, date_str))
    active_services = set(row['service_id'] for row in cursor.fetchall())

    cursor = conn.execute('SELECT service_id, exception_type FROM calendar_dates WHERE date = ?', (date_str,))
    for row in cursor.fetchall():
        if row['exception_type'] == GTFS_EXCEPTION_ADDED:
            active_services.add(row['service_id'])
        elif row['exception_type'] == GTFS_EXCEPTION_REMOVED and row['service_id'] in active_services:
            active_services.remove(row['service_id'])

    return active_services


@app.route(ROUTE_ROOT)
def index():
    return app.send_static_file(FILE_INDEX)


@app.route(ROUTE_API_STOPS)
def stops():
    q = request.args.get(PARAM_SEARCH_QUERY, '')
    if not q:
        return jsonify([])
    
    q_norm = unidecode(q).lower()
    conn = get_db()
    
    query = f'''
        SELECT DISTINCT stop_name 
        FROM stops 
        WHERE stop_name_normalized LIKE ? 
        LIMIT {LIMIT_SEARCH_STOPS}
    '''
    cursor = conn.execute(query, (SQL_WILDCARD + q_norm + SQL_WILDCARD,))
    results = [row['stop_name'] for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(results)


@app.route(ROUTE_API_DEPARTURES)
def departures():
    stop_name = request.args.get(PARAM_STOP_NAME)
    if not stop_name:
        return jsonify({JSON_KEY_ERROR: MSG_ERR_MISSING_STOP}), HTTP_STATUS_BAD_REQUEST

    now_dt = datetime.now(czech_tz)
    today_date = now_dt.date()
    yesterday_date = today_date - timedelta(days=DAYS_YESTERDAY_OFFSET)

    current_absolute_minutes = (HOURS_PER_DAY * MINUTES_PER_HOUR) + (now_dt.hour * MINUTES_PER_HOUR) + now_dt.minute

    conn = get_db()
    all_departures = []

    base_query = f'''
        SELECT r.route_short_name, t.trip_headsign, st.departure_time, s.platform_code
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s.stop_name = ? 
          AND st.departure_time >= ?
          AND t.service_id IN ({{placeholders}})
        LIMIT {LIMIT_DEPARTURES_DB}
    '''

    # --- 1. Fetch Yesterday's Night Routes ---
    services_yesterday = get_active_services(conn, yesterday_date)
    if services_yesterday:
        target_hour_yesterday = now_dt.hour + HOURS_PER_DAY
        target_time_str_yesterday = f'{target_hour_yesterday:02d}{STR_TIME_SPLIT_CHAR}{now_dt.minute:02d}{STR_TIME_SPLIT_CHAR}{SECONDS_ZERO_PADDED}'
        
        placeholders_y = ','.join(['?'] * len(services_yesterday))
        query_y = base_query.format(placeholders=placeholders_y)
        params_y = [stop_name, target_time_str_yesterday] + list(services_yesterday)
        
        for row in conn.execute(query_y, params_y).fetchall():
            time_parts = row['departure_time'].split(STR_TIME_SPLIT_CHAR)
            h = int(time_parts[IDX_TIME_HOUR])
            m = int(time_parts[IDX_TIME_MINUTE])
            dep_abs_minutes = (h * MINUTES_PER_HOUR) + m
            
            all_departures.append({
                'platform': row['platform_code'] or DEFAULT_PLATFORM_CODE,
                'headsign': row['trip_headsign'],
                'route': row['route_short_name'],
                'dep_abs_minutes': dep_abs_minutes,
                'departure_time': row['departure_time']
            })

    # --- 2. Fetch Today's Routes ---
    services_today = get_active_services(conn, today_date)
    if services_today:
        target_time_str_today = f'{now_dt.hour:02d}{STR_TIME_SPLIT_CHAR}{now_dt.minute:02d}{STR_TIME_SPLIT_CHAR}{SECONDS_ZERO_PADDED}'
        
        placeholders_t = ','.join(['?'] * len(services_today))
        query_t = base_query.format(placeholders=placeholders_t)
        params_t = [stop_name, target_time_str_today] + list(services_today)
        
        for row in conn.execute(query_t, params_t).fetchall():
            time_parts = row['departure_time'].split(STR_TIME_SPLIT_CHAR)
            h = int(time_parts[IDX_TIME_HOUR])
            m = int(time_parts[IDX_TIME_MINUTE])
            dep_abs_minutes = (HOURS_PER_DAY * MINUTES_PER_HOUR) + (h * MINUTES_PER_HOUR) + m
            
            all_departures.append({
                'platform': row['platform_code'] or DEFAULT_PLATFORM_CODE,
                'headsign': row['trip_headsign'],
                'route': row['route_short_name'],
                'dep_abs_minutes': dep_abs_minutes,
                'departure_time': row['departure_time']
            })

    conn.close()

    # --- 3. Merge, Filter, and Sort ---
    all_departures.sort(key=lambda x: x['dep_abs_minutes'])
    
    final_results = []
    seen_routes = set()

    for dep in all_departures:
        minutes_left = dep['dep_abs_minutes'] - current_absolute_minutes
        
        if minutes_left >= 0:
            unique_key = (dep['platform'], dep['headsign'], dep['route'])
            
            if unique_key not in seen_routes:
                seen_routes.add(unique_key)
                
                final_results.append({
                    'platform': dep['platform'],
                    'headsign': dep['headsign'],
                    'route': dep['route'],
                    'minutes_left': minutes_left,
                    'departure_time': dep['departure_time']
                })

    final_results.sort(key=lambda x: (x['platform'], x['headsign'], x['minutes_left']))

    return jsonify(final_results)


if __name__ == '__main__':
    app.run(debug=True, port=PORT_HTTP_SERVER)
