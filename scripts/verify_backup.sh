#!/usr/bin/env bash
# Verifica que existe un dump del día anterior en el directorio local de backups.
# Si no existe, registra el error en logs/verify_errors.log y sale con código 1.
# Pensado para ejecutarse vía cron diariamente, después del backup.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/verify.log"
ERROR_LOG="$LOG_DIR/verify_errors.log"
mkdir -p "$LOG_DIR"

log()    { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
logerr() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" | tee -a "$ERROR_LOG"; }

ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
fi

BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-$(dirname "$SCRIPT_DIR")/backups}"
BACKUP_LOCAL_DIR="$(realpath -m "$BACKUP_LOCAL_DIR")"

log "=== Verificación de backup iniciada ==="

# GNU date (Linux): date -d yesterday. BSD date (macOS): date -v -1d.
YESTERDAY="$(date -d "yesterday" '+%Y%m%d' 2>/dev/null || date -v -1d '+%Y%m%d')"

FOUND="$(find "$BACKUP_LOCAL_DIR" -name "dtcore_${YESTERDAY}*.sql.gz" 2>/dev/null | head -1)"

if [[ -n "$FOUND" ]]; then
  SIZE="$(du -h "$FOUND" | cut -f1)"
  log "OK — backup del $YESTERDAY encontrado: $(basename "$FOUND") ($SIZE)"
  log "=== Verificación OK ==="
  exit 0
else
  logerr "No se encontró backup del $YESTERDAY en $BACKUP_LOCAL_DIR"
  log "=== Verificación FALLÓ (exit 1) ==="
  exit 1
fi
