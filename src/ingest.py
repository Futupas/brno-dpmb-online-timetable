import sqlite3
import pandas as pd
from unidecode import unidecode
import os
import sys

# =============================================================================
# CONSTANTS
# =============================================================================

# Relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
GTFS_DIR = os.path.join(DATA_DIR, 'gtfs')
DB_PATH = os.path.join(DATA_DIR, 'transit.db')

# IDS JMK Zone IDs for Brno city
BRNO_ZONE_IDS = ['100', '101', '570']

# Padding length for HH:MM:SS
GTFS_TIME_LEN = 8

def normalize_string(s):
    if pd.isna(s):
        return s
    return unidecode(str(s)).lower()

def ingest():
    if not os.path.exists(GTFS_DIR):
        print('Error: GTFS directory not found: ' + GTFS_DIR)
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    print('Loading and filtering Brno stops...')
    stops = pd.read_csv(os.path.join(GTFS_DIR, 'stops.txt'), dtype=str)
    # Only keep stops belonging to Brno city zones
    brno_stops = stops[stops['zone_id'].isin(BRNO_ZONE_IDS)].copy()
    brno_stops['stop_name_normalized'] = brno_stops['stop_name'].apply(normalize_string)
    brno_stops.to_sql('stops', conn, if_exists='replace', index=False)

    # Get list of stop_ids to filter stop_times later (reduces DB size significantly)
    valid_stop_ids = set(brno_stops['stop_id'].unique())

    print('Loading routes...')
    routes = pd.read_csv(os.path.join(GTFS_DIR, 'routes.txt'), dtype=str)
    routes.to_sql('routes', conn, if_exists='replace', index=False)

    print('Loading trips...')
    trips = pd.read_csv(os.path.join(GTFS_DIR, 'trips.txt'), dtype=str)
    trips.to_sql('trips', conn, if_exists='replace', index=False)

    print('Loading stop_times (with padding and Brno filter)...')
    # We use a chunked approach to save memory on large datasets
    chunksize = 100000
    first_chunk = True
    for chunk in pd.read_csv(os.path.join(GTFS_DIR, 'stop_times.txt'), dtype=str, chunksize=chunksize):
        # Filter only for Brno stops
        filtered_chunk = chunk[chunk['stop_id'].isin(valid_stop_ids)].copy()
        if not filtered_chunk.empty:
            filtered_chunk['departure_time'] = filtered_chunk['departure_time'].str.zfill(GTFS_TIME_LEN)
            filtered_chunk.to_sql('stop_times', conn, if_exists='replace' if first_chunk else 'append', index=False)
            first_chunk = False

    print('Loading calendar...')
    for filename in ['calendar.txt', 'calendar_dates.txt']:
        path = os.path.join(GTFS_DIR, filename)
        if os.path.exists(path):
            df = pd.read_csv(path, dtype=str)
            df.to_sql(filename.replace('.txt', ''), conn, if_exists='replace', index=False)

    print('Creating indexes...')
    cursor = conn.cursor()
    cursor.execute('CREATE INDEX idx_stops_name_norm ON stops(stop_name_normalized);')
    cursor.execute('CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id);')
    cursor.execute('CREATE INDEX idx_stop_times_departure_time ON stop_times(departure_time);')
    cursor.execute('CREATE INDEX idx_trips_trip_id ON trips(trip_id);')
    conn.commit()
    conn.close()
    print('Done. Database created at ' + DB_PATH)

if __name__ == '__main__':
    ingest()
