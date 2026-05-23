#!/usr/bin/env bash
# Backup diario: pg_dump del contenedor + rclone copy a Google Drive.
# Variables leídas de .env en la raíz del proyecto (si existe); todas tienen default.
# Logs en scripts/logs/backup.log
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/backup.log"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# Cargar .env desde la raíz del proyecto
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
fi

DB_CONTAINER="${DB_CONTAINER:-dtcore-db}"
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-dtcore_db}"
BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-$(dirname "$SCRIPT_DIR")/backups}"
BACKUP_DRIVE_REMOTE_PATH="${BACKUP_DRIVE_REMOTE_PATH:-}"
RETENTION_DAYS_LOCAL="${RETENTION_DAYS_LOCAL:-30}"

BACKUP_LOCAL_DIR="$(realpath -m "$BACKUP_LOCAL_DIR")"
mkdir -p "$BACKUP_LOCAL_DIR"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
DUMP_FILE="$BACKUP_LOCAL_DIR/dtcore_${TIMESTAMP}.sql.gz"

log "=== Backup iniciado ==="
log "Contenedor: $DB_CONTAINER | Base: $DB_NAME | Archivo: $DUMP_FILE"

if ! docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$DUMP_FILE"; then
  log "ERROR: pg_dump falló"
  exit 1
fi

SIZE="$(du -h "$DUMP_FILE" | cut -f1)"
log "Dump local OK — tamaño: $SIZE"

if [[ -n "$BACKUP_DRIVE_REMOTE_PATH" ]]; then
  if ! rclone copy "$DUMP_FILE" "$BACKUP_DRIVE_REMOTE_PATH"; then
    log "ERROR: rclone copy falló — backup local disponible en $DUMP_FILE"
    exit 1
  fi
  log "rclone copy OK → $BACKUP_DRIVE_REMOTE_PATH"
else
  log "ADVERTENCIA: BACKUP_DRIVE_REMOTE_PATH no configurado, omitiendo upload a Drive"
fi

DELETED="$(find "$BACKUP_LOCAL_DIR" -name "dtcore_*.sql.gz" -mtime +"$RETENTION_DAYS_LOCAL" -print -delete | wc -l)"
[[ "$DELETED" -gt 0 ]] && log "Limpieza: $DELETED backup(s) locales eliminados (>$RETENTION_DAYS_LOCAL días)"

log "=== Backup completado OK ==="
