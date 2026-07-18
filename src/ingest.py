import sqlite3
import pandas as pd
from unidecode import unidecode
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
gtfs_dir = os.path.join(data_dir, 'GTFS')
db_path = os.path.join(data_dir, 'transit.db')
stops_file = os.path.join(data_dir, 'stops.csv')

def normalize_string(s):
    if pd.isna(s):
        return s
    return unidecode(str(s)).lower()

def ingest():
    if not os.path.exists(gtfs_dir):
        print('Error: Directory not found - ' + gtfs_dir)
        sys.exit(1)
        
    if not os.path.exists(stops_file):
        print('Error: Stops file not found - ' + stops_file)
        sys.exit(1)

    os.makedirs(data_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)

    print('Loading stops...')
    stops = pd.read_csv(stops_file, dtype=str)
    stops['stop_name_normalized'] = stops['stop_name'].apply(normalize_string)
    stops.to_sql('stops', conn, if_exists='replace', index=False)

    print('Loading routes...')
    routes = pd.read_csv(os.path.join(gtfs_dir, 'routes.txt'), dtype=str)
    routes.to_sql('routes', conn, if_exists='replace', index=False)

    print('Loading trips...')
    trips = pd.read_csv(os.path.join(gtfs_dir, 'trips.txt'), dtype=str)
    trips.to_sql('trips', conn, if_exists='replace', index=False)

    print('Loading stop_times...')
    stop_times = pd.read_csv(os.path.join(gtfs_dir, 'stop_times.txt'), dtype=str)
    stop_times.to_sql('stop_times', conn, if_exists='replace', index=False)

    print('Loading calendar...')
    calendar_path = os.path.join(gtfs_dir, 'calendar.txt')
    if os.path.exists(calendar_path):
        calendar = pd.read_csv(calendar_path, dtype=str)
        calendar.to_sql('calendar', conn, if_exists='replace', index=False)

    print('Loading calendar_dates...')
    calendar_dates_path = os.path.join(gtfs_dir, 'calendar_dates.txt')
    if os.path.exists(calendar_dates_path):
        calendar_dates = pd.read_csv(calendar_dates_path, dtype=str)
        calendar_dates.to_sql('calendar_dates', conn, if_exists='replace', index=False)

    print('Creating indexes...')
    cursor = conn.cursor()
    cursor.execute('CREATE INDEX idx_stops_name_norm ON stops(stop_name_normalized);')
    cursor.execute('CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id);')
    cursor.execute('CREATE INDEX idx_stop_times_trip_id ON stop_times(trip_id);')
    cursor.execute('CREATE INDEX idx_trips_trip_id ON trips(trip_id);')
    cursor.execute('CREATE INDEX idx_trips_route_id ON trips(route_id);')
    cursor.execute('CREATE INDEX idx_trips_service_id ON trips(service_id);')
    conn.commit()
    conn.close()
    print('Done. Database created at ' + db_path)

if __name__ == '__main__':
    ingest()
