#!/usr/bin/env sh

# Run ingestion if the database does not exist
if [ ! -f "../data/transit.db" ]; then
    echo "Database not found. Starting ingestion..."
    python ingest.py
fi

# Start the live collector in the background
echo "Starting Real-time Collector..."
python collector.py &

# Start the Flask app
echo "Starting Flask server..."
python app.py
