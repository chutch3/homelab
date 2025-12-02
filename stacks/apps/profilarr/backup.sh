#!/bin/sh

echo "Backup scheduler started..."
apk add --no-cache tzdata

while true; do
  DATE=$(date +%Y-%m-%d_%H-%M-%S)
  FILE="profilarr_backup_$DATE.tar.gz"
  echo "Creating backup: $FILE"
  tar -czf "/dest/$FILE" -C /source .

  # Keep only the 3 most recent backups
  echo "Cleaning up old backups (keeping 3 most recent)..."
  cd /dest || exit
  # shellcheck disable=SC2012
  ls -t profilarr_backup_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f
  REMAINING=$(find . -name "profilarr_backup_*.tar.gz" | wc -l)
  echo "Backups remaining: $REMAINING"

  echo "Backup done. Sleeping for 24 hours..."
  sleep 86400
done
