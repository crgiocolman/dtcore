#!/usr/bin/env bash
# Restaura un dump local al contenedor PostgreSQL.
# Uso: ./restore.sh <archivo.sql.gz>
# ADVERTENCIA: sobreescribe la base de datos completamente.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/restore.log"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <archivo.sql.gz>"
  echo "Ejemplo: $0 ../backups/dtcore_20250601_020000.sql.gz"
  exit 1
fi

DUMP_FILE="$(realpath "$1")"

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "Error: archivo no encontrado: $DUMP_FILE"
  exit 1
fi

ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
fi

DB_CONTAINER="${DB_CONTAINER:-dtcore-db}"
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-dtcore_db}"

log "=== Restore iniciado ==="
log "Archivo: $DUMP_FILE"
log "Contenedor: $DB_CONTAINER | Base: $DB_NAME"

echo ""
echo "ADVERTENCIA: esto sobreescribirá completamente la base de datos '$DB_NAME'."
echo "Archivo a restaurar: $DUMP_FILE"
echo ""
read -r -p "¿Continuar? [s/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[sS]$ ]]; then
  log "Restore cancelado por el usuario"
  echo "Cancelado."
  exit 0
fi

log "Terminando conexiones activas a $DB_NAME..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
  > /dev/null 2>&1 || true

log "Eliminando y recreando la base de datos..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS $DB_NAME;" > /dev/null
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres \
  -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" > /dev/null

log "Restaurando dump (esto puede tomar varios minutos)..."
if gunzip -c "$DUMP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -q; then
  log "=== Restore completado OK ==="
  echo "Restore completado. Verificar la aplicación."
else
  log "ERROR: restore falló — la base puede estar en estado inconsistente"
  echo "ERROR: restore falló. Revisar $LOG_FILE."
  exit 1
fi
