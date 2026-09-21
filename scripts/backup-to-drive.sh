#!/bin/sh
# Copies the database and uploaded protocols to Google Drive.
# One-time setup on the server, as the user that runs the site:
#   rclone config
# Name the remote "gdrive" and choose drive.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
STAMP=$(date +%Y%m%d-%H%M%S)
DB="$ROOT/data/db.sqlite3"
if [ ! -f "$DB" ]; then
  echo "No database at $DB" >&2
  exit 1
fi
mkdir -p "$ROOT/data/backups"
sqlite3 "$DB" ".backup '$ROOT/data/backups/db-$STAMP.sqlite3'"
rclone copy "$ROOT/data/backups/db-$STAMP.sqlite3" "gdrive:bg-powerlifting-results/db/"
if [ -d "$ROOT/media" ]; then
  rclone sync "$ROOT/media" "gdrive:bg-powerlifting-results/media" --exclude ".gitkeep" --exclude "imports/**"
fi
echo "Backup $STAMP copied to gdrive:bg-powerlifting-results/"
