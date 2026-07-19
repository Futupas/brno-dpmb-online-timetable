import sqlite3
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'transit.db')

def print_sequences():
    if not os.path.exists(DB_PATH):
        print(f'Error: Database not found at {DB_PATH}')
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. Get all unique routes
    routes = conn.execute('SELECT DISTINCT route_id, route_short_name FROM routes ORDER BY route_short_name').fetchall()

    for r in routes:
        short_name = r['route_short_name']
        
        # --- YOUR FILTER ---
        try:
            if int(short_name) > 12:
                continue
        except (ValueError, TypeError):
            continue
        # -------------------

        route_id = r['route_id']

        # 2. Find the "Longest" trip for this route to represent the main path
        trip = conn.execute('''
            SELECT t.trip_id, t.trip_headsign 
            FROM trips t 
            JOIN stop_times st ON t.trip_id = st.trip_id
            WHERE t.route_id = ? 
            GROUP BY t.trip_id 
            ORDER BY COUNT(st.stop_id) DESC 
            LIMIT 1
        ''', (route_id,)).fetchone()

        if not trip:
            continue

        trip_id = trip['trip_id']
        headsign = trip['trip_headsign']

        # 3. Get all stops for this trip
        # We CAST stop_sequence to INTEGER to fix the ordering bug
        stops = conn.execute('''
            SELECT s.stop_id, s.stop_name, st.stop_sequence
            FROM stop_times st
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE st.trip_id = ?
            ORDER BY CAST(st.stop_sequence AS INTEGER) ASC
        ''', (trip_id,)).fetchall()

        # 4. Format exactly as requested
        stop_list = []
        for i, s in enumerate(stops, 1):
            stop_list.append(f"{i}. {s['stop_id']} {s['stop_name']}")
        
        stop_chain = ' -> '.join(stop_list)
        print(f"Route {short_name} (to {headsign}):\n{stop_chain}\n")
        print('-' * 30)

    conn.close()

if __name__ == '__main__':
    print_sequences()
