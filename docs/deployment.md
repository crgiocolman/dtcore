# docs/deployment.md — Guía de deployment DTCore

Pasos para desplegar DTCore en la PC-servidor del cliente. Asume Ubuntu/Debian 22.04+. Para Windows con WSL2, los comandos de bash son idénticos dentro de la sesión WSL.

---

## Pre-requisitos

- Docker Engine + Docker Compose v2 instalados (`docker compose version`)
- `rclone` instalado: `curl https://rclone.org/install.sh | sudo bash`
- Node.js 20+ (solo necesario si se hace build del frontend en la PC-servidor; en producción el build ya viene en la imagen Docker)
- El repo clonado: `git clone <repo> dtcore && cd dtcore`
- Archivo `.env` creado desde `.env.example` (ver sección siguiente)

---

## Variables de entorno (.env)

Crear `.env` en la raíz del proyecto. Nunca commitear este archivo.

```bash
# Base de datos
DATABASE_URL=postgresql+asyncpg://admin:CAMBIAR_PASSWORD@localhost:5432/dtcore_db
DB_CONTAINER=dtcore-db
DB_USER=admin
DB_NAME=dtcore_db

# Auth
JWT_SECRET=CAMBIAR_POR_SECRETO_ALEATORIO_LARGO
JWT_EXPIRES_HOURS=8

# Storage (archivos subidos por la app)
STORAGE_PATH=/var/dtcore/storage

# Backups
BACKUP_LOCAL_DIR=/var/dtcore/backups
BACKUP_DRIVE_REMOTE_PATH=gdrive:DTCore/backups
RETENTION_DAYS_LOCAL=30
```

Para generar un `JWT_SECRET` seguro:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Configurar rclone con Google Drive

Solo necesario una vez por instalación. rclone necesita acceso a la cuenta de Drive del cliente.

### 1. Iniciar la configuración interactiva

```bash
rclone config
```

### 2. Seguir el wizard

```
n) New remote
name> gdrive
Storage> drive          # Google Drive
client_id>              # dejar vacío (usar cliente por defecto de rclone)
client_secret>          # dejar vacío
scope> 1                # drive (acceso completo)
root_folder_id>         # dejar vacío
service_account_file>   # dejar vacío
Edit advanced config? n
Use web browser to authenticate? n   # si estamos en servidor sin GUI
```

Si el servidor no tiene navegador (headless), rclone imprime una URL. Abrirla en cualquier otro dispositivo con la cuenta de Drive del cliente, autorizar, y pegar el código de vuelta.

### 3. Verificar el acceso

```bash
rclone ls gdrive:
rclone mkdir gdrive:DTCore/backups
rclone ls gdrive:DTCore/backups
```

### 4. Probar el backup manualmente

```bash
cd /ruta/al/proyecto
bash scripts/backup.sh
# Verificar que aparece el archivo en Drive
rclone ls gdrive:DTCore/backups
```

---

## Configurar cron para backups automáticos

### 1. Hacer los scripts ejecutables

```bash
chmod +x scripts/backup.sh scripts/verify_backup.sh scripts/restore.sh
```

### 2. Editar el crontab del usuario que corre Docker

```bash
crontab -e
```

Agregar estas líneas (ajustar la ruta al proyecto):

```cron
# Backup diario a las 2:00 AM
0 2 * * * /ruta/al/proyecto/scripts/backup.sh >> /ruta/al/proyecto/scripts/logs/cron.log 2>&1

# Verificación diaria a las 7:00 AM (después del backup)
0 7 * * * /ruta/al/proyecto/scripts/verify_backup.sh >> /ruta/al/proyecto/scripts/logs/cron.log 2>&1
```

### 3. Verificar que cron está corriendo

```bash
systemctl status cron    # Ubuntu/Debian
# o
systemctl status crond   # CentOS/RHEL
```

### 4. Probar que el cron corre correctamente

```bash
# Simular corrida manual
bash scripts/backup.sh

# Ver logs
tail -50 scripts/logs/backup.log
tail -50 scripts/logs/verify.log

# Ver errores de verificación (si los hay)
cat scripts/logs/verify_errors.log
```

---

## Restaurar un backup en caso de desastre

### Caso 1: Tengo el archivo .sql.gz localmente

```bash
# Verificar que el contenedor de PostgreSQL está corriendo
docker ps | grep dtcore-db

# Restaurar
bash scripts/restore.sh backups/dtcore_20250601_020000.sql.gz
```

El script pide confirmación interactiva antes de borrar la base. Confirmar con `s`.

### Caso 2: Solo tengo el archivo en Drive

```bash
# Listar backups disponibles en Drive
rclone ls gdrive:DTCore/backups

# Descargar el backup del día que se necesita
mkdir -p backups
rclone copy "gdrive:DTCore/backups/dtcore_20250601_020000.sql.gz" backups/

# Restaurar
bash scripts/restore.sh backups/dtcore_20250601_020000.sql.gz
```

### Caso 3: Restaurar en PC nueva (desastre total)

1. Instalar Docker + rclone en la PC nueva
2. Clonar el repo
3. Crear `.env` con las credenciales correctas
4. Levantar el contenedor de PostgreSQL: `docker compose up -d db`
5. Configurar rclone con la cuenta de Drive del cliente (ver sección anterior)
6. Descargar el último backup desde Drive y restaurar (ver Caso 2)
7. Levantar el resto de la app: `docker compose up -d`

---

## Monitoreo de logs

```bash
# Ver últimos backups
tail -30 scripts/logs/backup.log

# Ver historial de verificaciones
tail -30 scripts/logs/verify.log

# Ver solo errores de verificación (vacío = todo OK)
cat scripts/logs/verify_errors.log

# Ver dumps locales disponibles
ls -lh backups/

# Ver cuánto espacio ocupan
du -sh backups/
```

---

## Retención de backups

| Destino | Retención | Configurable vía |
|---|---|---|
| Local (`backups/`) | 30 días | `RETENTION_DAYS_LOCAL` en `.env` |
| Google Drive | Manual (no se borran automáticamente en v1) | — |

En v1, los backups en Drive no se limpian automáticamente. Con 30 días a un ritmo de ~1-5 MB por dump, el espacio en Drive no es un problema práctico a corto plazo. Si se quiere limpiar, ejecutar `rclone delete --min-age 90d gdrive:DTCore/backups` manualmente.

---

## Troubleshooting

**`pg_dump: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed`**
→ El contenedor `dtcore-db` no está corriendo. `docker compose up -d db`

**`rclone: command not found`**
→ rclone no instalado o no en PATH. `which rclone` para verificar.

**`Error opening config file... no config found`**
→ rclone no configurado. Ejecutar `rclone config` (ver sección anterior).

**El backup corre pero Drive no tiene el archivo**
→ Verificar `BACKUP_DRIVE_REMOTE_PATH` en `.env`. Probar `rclone ls gdrive:DTCore/backups`. Si da error de auth, reconectar: `rclone config reconnect gdrive:`.

**Token de Google expirado**
→ rclone renueva el token automáticamente si hay acceso a internet. Si falla: `rclone config reconnect gdrive:` desde la misma sesión donde se pueda autorizar un browser.
