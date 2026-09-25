#!/usr/bin/env sh
# Daily backup of the SQLite database from the running container (add to cron):
#   0 3 * * * /path/to/repo/deploy/backup.sh /root/backups
set -eu
DEST="${1:-./backups}"
mkdir -p "$DEST"
COMPOSE="docker compose -f $(dirname "$0")/docker-compose.prod.yml"
STAMP=$(date +%Y%m%d-%H%M%S)
$COMPOSE exec -T app python -c "
import sqlite3
src = sqlite3.connect('/data/app.db')
dst = sqlite3.connect('/data/backup.db')
src.backup(dst)
dst.close()
"
$COMPOSE cp app:/data/backup.db "$DEST/app-$STAMP.db"
find "$DEST" -name 'app-*.db' -mtime +14 -delete
echo "saved $DEST/app-$STAMP.db"
