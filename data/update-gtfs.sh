#!/usr/bin/env bash

# Used to update STATIC GTFS data. Should be ran every Sunday after 12:00 (Czech time)
# Details: https://data.brno.cz/datasets/jízdní-řád-ids-jmk-ve-formátu-gtfs-gtfs-timetable-data/about

# exit on error, treat unset variables as errors, the exit status of a pipeline is the status of the last command
set -euo pipefail

# Resolve the directory where this script is located
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

ZIP_FILE="$SCRIPT_DIR/gtfs.zip"
GTFS_DIR="$SCRIPT_DIR/gtfs"
OLD_DIR="$SCRIPT_DIR/gtfs.old"
URL="https://kordis-jmk.cz/gtfs/gtfs.zip"

# 1. Remove existing ZIP if it exists
rm -f "$ZIP_FILE"

# Just in case
rm -f "$SCRIPT_DIR/live_delays.json"
rm -f "$SCRIPT_DIR/transit.db"

# 2. Download the new ZIP
curl -fL "$URL" -o "$ZIP_FILE"

# 3. Rename existing gtfs directory to gtfs.old
if [[ -d "$GTFS_DIR" ]]; then
    rm -rf "$OLD_DIR"
    mv "$GTFS_DIR" "$OLD_DIR"
fi

# Ensure cleanup on failure
cleanup() {
    if [[ $? -ne 0 ]]; then
        echo "Extraction failed, restoring previous GTFS directory..."
        rm -rf "$GTFS_DIR"
        if [[ -d "$OLD_DIR" ]]; then
            mv "$OLD_DIR" "$GTFS_DIR"
        fi
    fi
}
trap cleanup EXIT

# 4. Unzip
mkdir -p "$SCRIPT_DIR/gtfs"
unzip -q "$ZIP_FILE" -d "$SCRIPT_DIR/gtfs"

# 5. Success: remove backup
rm -rf "$OLD_DIR"

# Disable the failure cleanup trap
trap - EXIT

echo "GTFS update completed successfully."
