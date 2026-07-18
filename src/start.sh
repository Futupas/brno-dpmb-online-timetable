#!/usr/bin/env sh

# This is for Docker only

# Run ingestion if the database does not exist
if [ ! -f "../data/transit.db" ]; then
    echo "Database not found at ../data/transit.db. Starting ingestion..."
    python ingest.py
else
    echo "Database exists. Skipping ingestion."
fi

# Start the Flask app
echo "Starting Flask server..."
python app.py
