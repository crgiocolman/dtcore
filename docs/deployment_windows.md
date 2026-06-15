# docs/deployment_windows.md — Deployment nativo en Windows

Deployment de DTCore directamente en Windows, sin Docker. Para clientes sin virtualización habilitada o con PCs de bajos recursos donde Docker es overhead injustificado.

---

## Pre-requisitos

Instalar en orden. Todos requieren permisos de administrador.

- **Windows** 10 / 11
- **Python** 3.12+ — [python.org](https://python.org) · marcar **"Add to PATH"** al instalar
- **Node.js** 20 LTS — [nodejs.org](https://nodejs.org) · installer LTS
- **PostgreSQL** 16 — Instalador EDB en [enterprisedb.com](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
- **Git para Windows** último — [git-scm.com](https://git-scm.com)
- **NSSM** último — [nssm.cc](https://nssm.cc/download) · descomprimir, copiar `nssm.exe` a `C:\dtcore\tools\`
- **mkcert** último — [github.com/FiloSottile/mkcert](https://github.com/FiloSottile/mkcert/releases) · copiar `mkcert.exe` a `C:\dtcore\tools\`
- **rclone** último — [rclone.org](https://rclone.org/downloads/) · copiar `rclone.exe` a `C:\dtcore\tools\`

Verificar instalaciones antes de continuar:

```powershell
python --version        # Python 3.12.x
node --version          # v20.x.x
npm --version           # 10.x.x
git --version           # git version 2.x.x
psql --version          # psql (PostgreSQL) 16.x
```

---

## Estructura de directorios

```
C:\dtcore\
  backend\          ← código backend + venv
  frontend\         ← código frontend
  logs\             ← logs de servicios y backups
  tools\            ← nssm.exe, mkcert.exe, rclone.exe
  backups\          ← dumps locales de PostgreSQL
  certs\            ← certificados TLS generados con mkcert
  scripts\          ← backup.ps1
```

Crear la estructura base:

```powershell
New-Item -ItemType Directory -Force C:\dtcore\logs
New-Item -ItemType Directory -Force C:\dtcore\tools
New-Item -ItemType Directory -Force C:\dtcore\backups
New-Item -ItemType Directory -Force C:\dtcore\certs
New-Item -ItemType Directory -Force C:\dtcore\scripts
```

---

## Clonar el repositorio

El repositorio es público en GitHub — no se necesitan credenciales ni configuración de git para clonar ni para hacer `git pull` durante actualizaciones.

```powershell
cd C:\
git clone https://github.com/crgiocolman/dtcore.git dtcore
cd C:\dtcore
```

Verificar que la clonación fue correcta:

```powershell
git log --oneline -3
# Debe mostrar los últimos commits del proyecto
```

---

## Instalación de PostgreSQL

### 1. Instalar con el wizard de EDB

Ejecutar el instalador descargado de EnterpriseDB. El wizard tiene estas pantallas en orden:

1. **Installation Directory** — dejar default (`C:\Program Files\PostgreSQL\16`)
2. **Select Components** — dejar todos marcados (Server, pgAdmin 4, Stack Builder, Command Line Tools)
3. **Data Directory** — dejar default (`C:\Program Files\PostgreSQL\16\data`)
4. **Password** — **ingresar y confirmar la contraseña del superuser `postgres`. ANOTARLA — se usa en el paso siguiente y nunca más.**
5. **Port** — dejar `5432`
6. **Advanced Options — Locale** — cambiar a **Spanish, Paraguay** (buscar "Paraguay" en el dropdown). Si no aparece, usar Default.
7. **Pre Installation Summary** — revisar y continuar
8. **Ready to Install** — instalar

Al terminar, el wizard ofrece abrir Stack Builder — cerrarlo, no es necesario.

PostgreSQL se registra automáticamente como servicio de Windows con inicio automático (`postgresql-x64-16`).

### 2. Agregar psql al PATH del sistema

Hacer esto primero, así los comandos siguientes son más cortos. Ejecutar PowerShell como Administrador:

```powershell
$pgBin = "C:\Program Files\PostgreSQL\16\bin"
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
[Environment]::SetEnvironmentVariable("PATH", "$currentPath;$pgBin", "Machine")
# Cerrar y reabrir PowerShell para que tome efecto, luego verificar:
psql --version   # psql (PostgreSQL) 16.x
```

### 3. Crear usuario y base de datos

Abrir **una nueva PowerShell como Administrador** (para que tome el PATH actualizado) y conectar como superuser:

```powershell
psql -U postgres -h localhost
```

Pide la contraseña del superuser `postgres` que se ingresó durante el wizard. Una vez dentro:

```sql
CREATE USER dtcore_admin WITH PASSWORD 'CAMBIAR_PASSWORD_SEGURA';
CREATE DATABASE dtcore_db OWNER dtcore_admin;
-- Verificar que se crearon:
\du dtcore_admin
\l dtcore_db
\q
```

Elegir una contraseña segura para `dtcore_admin`. Esta contraseña se usa en el `.env` del backend, en el script de backup, y en los comandos de restauración — anotarla en el documento del cliente.

### 4. Verificar la conexión con el usuario de app

```powershell
psql -U dtcore_admin -d dtcore_db -h localhost
# Pide la contraseña de dtcore_admin
# Debe entrar al prompt: dtcore_db=>
# Salir con \q
```

---

## Instalación del backend

```powershell
cd C:\dtcore\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell rechaza el script de activación por política de ejecución:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Variables de entorno (.env)

Crear `C:\dtcore\backend\.env`. Nunca commitear este archivo.

```env
DATABASE_URL=postgresql+asyncpg://dtcore_admin:CAMBIAR_PASSWORD_SEGURA@localhost:5432/dtcore_db
JWT_SECRET=CAMBIAR_POR_SECRETO_ALEATORIO_LARGO
JWT_EXPIRES_HOURS=8
STORAGE_PATH=C:\dtcore\storage
BACKUP_LOCAL_DIR=C:\dtcore\backups
BACKUP_DRIVE_REMOTE_PATH=gdrive:DTCore/backups
RETENTION_DAYS_LOCAL=30
```

Generar un `JWT_SECRET` seguro:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### Migraciones y seed

```powershell
cd C:\dtcore\backend
.venv\Scripts\Activate.ps1
alembic upgrade head
python -m app.seed.run
```

### Probar el backend

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Abrir http://localhost:8000/docs — debe mostrar la documentación de la API
# Ctrl+C para detener
```

---

## Generación de certificados TLS con mkcert

Necesario para que la PWA funcione en dispositivos del cliente via LAN.

### 1. Instalar la CA raíz de mkcert en la PC-servidor

```powershell
cd C:\dtcore\tools
.\mkcert.exe -install
```

### 2. Generar el certificado

Reemplazar `<ip-lan>` con la IP fija de la PC-servidor (ej. `192.168.1.100`):

```powershell
cd C:\dtcore\certs
C:\dtcore\tools\mkcert.exe localhost 127.0.0.1 <ip-lan>
```

mkcert genera dos archivos con nombres que dependen de los dominios pasados. Ver exactamente cómo se llamaron:

```powershell
dir C:\dtcore\certs\
# Ejemplo de salida:
#   localhost+2.pem          ← certificado
#   localhost+2-key.pem      ← clave privada
#
# Si la IP contiene puntos en el nombre el archivo puede llamarse diferente,
# por ejemplo: localhost+2.pem o _wildcard.+2.pem
# Anotar los nombres exactos — se necesitan en la config de nginx del paso siguiente.
```

---

## Instalación del frontend

```powershell
cd C:\dtcore\frontend
npm install
```

### Variables de entorno (.env)

Crear `C:\dtcore\frontend\.env.production`:

```env
VITE_API_URL=https://<ip-lan>/api
```

### Build de producción

```powershell
cd C:\dtcore\frontend
npm run build
```

### Probar el frontend (temporal, sin HTTPS)

```powershell
npx serve -s dist -l 4173
# Abrir http://localhost:4173 — debe cargar la app
# Ctrl+C para detener
```

---

## Configuración del servidor web con nginx

`npx serve` no es adecuado para producción. Usar nginx para Windows para servir el build del frontend y actuar como reverse proxy del backend.

### 1. Descargar nginx para Windows

Descargar desde [nginx.org](https://nginx.org/en/download.html) (Stable version, ZIP). Descomprimir en `C:\dtcore\nginx`.

### 2. Configurar nginx

Editar `C:\dtcore\nginx\conf\nginx.conf`:

```nginx
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;

    server {
        listen 443 ssl;
        server_name localhost <ip-lan>;

        ssl_certificate     C:/dtcore/certs/localhost+2.pem;
        ssl_certificate_key C:/dtcore/certs/localhost+2-key.pem;

        # Frontend
        root C:/dtcore/frontend/dist;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        # Backend API
        location /api/ {
            proxy_pass http://127.0.0.1:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # Redirigir HTTP → HTTPS
    server {
        listen 80;
        return 301 https://$host$request_uri;
    }
}
```

Reemplazar `localhost+2.pem` y `localhost+2-key.pem` con los nombres exactos que mostró el `dir` del paso anterior.

### 3. Probar nginx

```powershell
cd C:\dtcore\nginx
.\nginx.exe -t        # debe imprimir "syntax is ok" y "test is successful"
.\nginx.exe           # arranca nginx en foreground
# Abrir https://localhost en el browser (debe cargar la app sin error de certificado)
# Para detener: .\nginx.exe -s stop
```

---

## Arranque automático con NSSM

Configurar tres servicios de Windows: backend (uvicorn), nginx, y dejar PostgreSQL que ya se autogestiona.

> **Alternativa GUI**: ejecutar `.\nssm.exe install <nombre-servicio>` sin argumentos extra abre una interfaz gráfica donde se pueden ingresar todos los valores visualmente. Útil si algún parámetro tiene caracteres especiales o si se prefiere revisar la configuración campo por campo.

### Servicio dtcore-backend

```powershell
cd C:\dtcore\tools

.\nssm.exe install dtcore-backend "C:\dtcore\backend\.venv\Scripts\uvicorn.exe"
.\nssm.exe set dtcore-backend AppParameters "app.main:app --host 0.0.0.0 --port 8000"
.\nssm.exe set dtcore-backend AppDirectory "C:\dtcore\backend"
.\nssm.exe set dtcore-backend AppEnvironmentExtra "PYTHONPATH=C:\dtcore\backend"
.\nssm.exe set dtcore-backend AppStdout "C:\dtcore\logs\backend.log"
.\nssm.exe set dtcore-backend AppStderr "C:\dtcore\logs\backend.log"
.\nssm.exe set dtcore-backend AppRotateFiles 1
.\nssm.exe set dtcore-backend AppRotateBytes 10485760
.\nssm.exe set dtcore-backend Start SERVICE_AUTO_START
.\nssm.exe set dtcore-backend ObjectName "LocalSystem"
```

### Servicio dtcore-nginx

nginx en Windows gestiona sus propios procesos worker internamente, lo que puede interferir con cómo NSSM detecta si el proceso está vivo. Los parámetros adicionales le dicen a NSSM que mate el árbol completo de procesos al detener, evitando workers huérfanos:

```powershell
.\nssm.exe install dtcore-nginx "C:\dtcore\nginx\nginx.exe"
.\nssm.exe set dtcore-nginx AppDirectory "C:\dtcore\nginx"
.\nssm.exe set dtcore-nginx AppStdout "C:\dtcore\logs\nginx.log"
.\nssm.exe set dtcore-nginx AppStderr "C:\dtcore\logs\nginx.log"
.\nssm.exe set dtcore-nginx AppKillProcessTree 1
.\nssm.exe set dtcore-nginx AppStopMethodConsole 1500
.\nssm.exe set dtcore-nginx AppStopMethodWindow 1500
.\nssm.exe set dtcore-nginx Start SERVICE_AUTO_START
.\nssm.exe set dtcore-nginx ObjectName "LocalSystem"
```

> Para recargar la configuración de nginx sin reiniciar el servicio completo (por ejemplo, después de renovar certificados):
>
> ```powershell
> C:\dtcore\nginx\nginx.exe -s reload
> ```

### Arrancar los servicios

```powershell
.\nssm.exe start dtcore-backend
.\nssm.exe start dtcore-nginx

# Verificar estado
.\nssm.exe status dtcore-backend   # debe imprimir SERVICE_RUNNING
.\nssm.exe status dtcore-nginx     # debe imprimir SERVICE_RUNNING
```

### Verificación final de servicios

```powershell
# Ver todos los servicios DTCore
Get-Service | Where-Object { $_.Name -like "*dtcore*" -or $_.Name -like "postgresql*" }
```

---

## Configuración de firewall de Windows

Permitir tráfico entrante en los puertos necesarios desde la red local.

```powershell
# Ejecutar como Administrador

# HTTPS (nginx)
New-NetFirewallRule -DisplayName "DTCore HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -Profile Private

# HTTP (redirigir a HTTPS, opcional)
New-NetFirewallRule -DisplayName "DTCore HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Profile Private

# Backend (solo para debug interno, no necesario en producción)
# New-NetFirewallRule -DisplayName "DTCore Backend" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

---

## Configuración de IP fija en la PC-servidor

> **Si estás haciendo esto de forma remota:** leer esta sección completa antes de tocar cualquier cosa. El paso del paracaídas es obligatorio — si la IP queda mal configurada, el sistema se recupera solo sin necesitar intervención física.

### Paso 1 — Anotar la configuración de red actual

Antes de cambiar nada, registrar los valores actuales. Abrir PowerShell y ejecutar:

```powershell
ipconfig /all
```

Buscar el adaptador activo (el que tiene "IPv4 Address" asignada) y anotar:

- **Nombre del adaptador** — ej. `Ethernet`, `Wi-Fi`, `Ethernet 2`
- **IPv4 Address** — la IP actual, ej. `192.168.1.55`
- **Subnet Mask** — normalmente `255.255.255.0`
- **Default Gateway** — el router, ej. `192.168.1.1`
- **DNS Servers** — ej. `192.168.1.1` o `8.8.8.8`

Elegir la IP fija que se va a asignar — debe estar en el mismo rango que la actual (mismo prefijo `192.168.1.xxx`) y **fuera del rango DHCP del router** para evitar conflictos. En la mayoría de routers hogareños el DHCP reparte desde `.100` en adelante, así que valores entre `.2` y `.99` suelen ser seguros. Ej: `192.168.1.10`.

### Paso 2 — Crear el paracaídas (obligatorio si estás en remoto)

Este paso crea una tarea programada que revierte la PC a DHCP automáticamente a los **7 minutos**. Si la nueva IP queda mal y perdés la sesión remota, la PC se recupera sola y podés volver a conectarte con la IP original.

Ejecutar en PowerShell como Administrador (reemplazar `"Ethernet"` con el nombre del adaptador anotado en el paso anterior):

```powershell
$iface = "Ethernet"   # <-- cambiar si el adaptador tiene otro nombre
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -Command `"Set-NetIPInterface -InterfaceAlias '$iface' -Dhcp Enabled; Set-DnsClientServerAddress -InterfaceAlias '$iface' -ResetServerAddresses`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(7)
Register-ScheduledTask -TaskName "DTCore-IPRollback" -Action $action -Trigger $trigger -RunLevel Highest -User "SYSTEM" -Force
Write-Host "Paracaídas activo — la PC revertirá a DHCP en 7 minutos si no lo cancelás."
```

### Paso 3 — Cambiar la IP via la interfaz gráfica de Windows

Seguir estos pasos con cuidado, verificando cada valor antes de confirmar:

1. Presionar **Win + R**, escribir `ncpa.cpl` y presionar Enter. Se abre la ventana de **Conexiones de red**.
2. Identificar el adaptador activo (el mismo del paso 1). Hacer **clic derecho → Propiedades**.
3. En la lista, seleccionar **"Protocolo de Internet versión 4 (TCP/IPv4)"** y hacer clic en **Propiedades**.
4. Seleccionar **"Usar la siguiente dirección IP"** y completar con los valores anotados:
   - **Dirección IP:** la IP fija elegida, ej. `192.168.1.10`
   - **Máscara de subred:** la misma que estaba, ej. `255.255.255.0`
   - **Puerta de enlace predeterminada:** exactamente igual que antes, ej. `192.168.1.1`
5. En la sección DNS, seleccionar **"Usar las siguientes direcciones de servidor DNS"**:
   - **Servidor DNS preferido:** `8.8.8.8`
   - **Servidor DNS alternativo:** `8.8.4.4`
6. **Hacer clic en Aceptar → Aceptar → Cerrar.** La conexión se interrumpe brevemente mientras aplica.

### Paso 4 — Verificar conectividad

Inmediatamente después de aplicar el cambio, antes de que pase el tiempo del paracaídas:

```powershell
# Verificar que la IP fija quedó asignada
ipconfig | findstr "IPv4"

# Verificar acceso al router (gateway)
ping 192.168.1.1 -n 3    # reemplazar con el gateway real

# Verificar acceso a internet
ping 8.8.8.8 -n 3
```

Si los tres comandos responden bien: todo OK, continuar al paso 5.

Si `ping 192.168.1.1` falla pero `ping 8.8.8.8` responde (o viceversa): hay un problema de configuración. Esperar los 7 minutos del paracaídas — la PC va a volver a DHCP automáticamente y vas a poder reconectarte.

### Paso 5 — Cancelar el paracaídas

Una vez confirmado que la conectividad funciona, eliminar la tarea para que no revierta la IP:

```powershell
Unregister-ScheduledTask -TaskName "DTCore-IPRollback" -Confirm:$false
Write-Host "Paracaídas cancelado. IP fija confirmada."
```

---

### Alternativa: configurar la IP fija por PowerShell

Si se prefiere terminal en lugar de la UI gráfica, usar estos comandos **después de crear el paracaídas del paso 2**:

```powershell
# Reemplazar los valores con los anotados en el paso 1
$iface   = "Ethernet"
$ip      = "192.168.1.10"
$mask    = 24                  # 24 = 255.255.255.0
$gateway = "192.168.1.1"

# Eliminar la IP actual asignada por DHCP antes de asignar la estática
$current = Get-NetIPAddress -InterfaceAlias $iface -AddressFamily IPv4 -ErrorAction SilentlyContinue
if ($current) { Remove-NetIPAddress -InterfaceAlias $iface -AddressFamily IPv4 -Confirm:$false }

# Eliminar la ruta de gateway actual
$route = Get-NetRoute -InterfaceAlias $iface -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue
if ($route) { Remove-NetRoute -InterfaceAlias $iface -DestinationPrefix "0.0.0.0/0" -Confirm:$false }

# Asignar IP fija
New-NetIPAddress -InterfaceAlias $iface -IPAddress $ip -PrefixLength $mask -DefaultGateway $gateway
Set-DnsClientServerAddress -InterfaceAlias $iface -ServerAddresses "8.8.8.8", "8.8.4.4"
```

Luego verificar y cancelar el paracaídas igual que en los pasos 4 y 5.

---

## Importar certificado mkcert en dispositivos del cliente

Los dispositivos que van a acceder a la app por LAN necesitan confiar en la CA de mkcert.

### Exportar la CA

```powershell
# En la PC-servidor, obtener la ruta de la CA
C:\dtcore\tools\mkcert.exe -CAROOT
# Típicamente: C:\Users\<usuario>\AppData\Local\mkcert
# El archivo a distribuir es rootCA.pem
```

### Instalar en otros dispositivos Windows

Copiar `rootCA.pem` al dispositivo (USB o carpeta compartida) y:

```powershell
# En el dispositivo cliente, ejecutar como Administrador
Import-Certificate -FilePath "C:\ruta\a\rootCA.pem" -CertStoreLocation Cert:\LocalMachine\Root
```

### Instalar en Android / iOS

Ver [documentación de mkcert](https://github.com/FiloSottile/mkcert?tab=readme-ov-file#mobile-devices) para el procedimiento por plataforma.

---

## Configuración de backups

### Archivo de credenciales para backup

La contraseña de la base de datos no debe quedar escrita en el script (el script queda en git). Se guarda en un archivo separado con permisos restringidos. Hacer esto **una sola vez** durante el deploy:

```powershell
# Ejecutar como Administrador
$credsFile = "C:\dtcore\scripts\.pgcreds"
Set-Content $credsFile "CAMBIAR_PASSWORD_SEGURA" -Encoding UTF8 -NoNewline

# Restringir acceso: solo SYSTEM y Administradores pueden leerlo
icacls $credsFile /inheritance:r /grant "SYSTEM:(R)" /grant "Administrators:(R)"

# Verificar que quedó bien
icacls $credsFile
# Debe mostrar solo SYSTEM y Administrators, sin "Users" ni otros
```

Reemplazar `CAMBIAR_PASSWORD_SEGURA` con la contraseña real de `dtcore_admin`.

### Script de backup

Crear `C:\dtcore\scripts\backup.ps1`:

```powershell
# backup.ps1 — Backup diario de PostgreSQL con upload a Google Drive
$ErrorActionPreference = "Stop"

$timestamp    = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir    = "C:\dtcore\backups"
$logFile      = "C:\dtcore\logs\backup.log"
$rclone       = "C:\dtcore\tools\rclone.exe"
$pgDump       = "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
$dumpFile     = "$backupDir\dtcore_$timestamp.sql"
$archiveFile  = "$backupDir\dtcore_$timestamp.zip"
$remotePath   = "gdrive:DTCore/backups"
$retentionDays = 30

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
    Write-Host $line
}

try {
    Log "=== Inicio backup ==="

    # Leer credencial desde archivo externo (no se guarda la password en este script)
    $credsFile = "C:\dtcore\scripts\.pgcreds"
    if (-not (Test-Path $credsFile)) { throw "Archivo de credenciales no encontrado: $credsFile" }
    $env:PGPASSWORD = (Get-Content $credsFile -Raw).Trim()

    # Dump PostgreSQL
    & $pgDump -U dtcore_admin -h localhost -d dtcore_db -F p -f $dumpFile
    if ($LASTEXITCODE -ne 0) { throw "pg_dump falló con código $LASTEXITCODE" }
    Log "pg_dump completado: $dumpFile"

    # Comprimir
    Compress-Archive -Path $dumpFile -DestinationPath $archiveFile -Force
    Remove-Item $dumpFile
    $size = (Get-Item $archiveFile).Length / 1MB
    Log "Comprimido: $archiveFile ($([math]::Round($size, 2)) MB)"

    # Subir a Drive
    & $rclone copy $archiveFile $remotePath --log-level INFO
    if ($LASTEXITCODE -ne 0) { throw "rclone copy falló con código $LASTEXITCODE" }
    Log "Upload a Drive completado"

    # Retención local: borrar dumps más viejos que $retentionDays días
    $cutoff = (Get-Date).AddDays(-$retentionDays)
    Get-ChildItem $backupDir -Filter "dtcore_*.zip" |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object { Remove-Item $_.FullName; Log "Eliminado backup antiguo: $($_.Name)" }

    Log "=== Backup completado OK ==="
} catch {
    Log "ERROR: $_"
    exit 1
}
```

### Tarea programada en Task Scheduler

```powershell
# Ejecutar como Administrador
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
               -Argument "-NonInteractive -File C:\dtcore\scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
               -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "DTCore Backup" `
    -Action $action -Trigger $trigger -Settings $settings `
    -RunLevel Highest -User "SYSTEM"
```

Probar la tarea manualmente:

```powershell
Start-ScheduledTask -TaskName "DTCore Backup"
# Esperar ~30 segundos y verificar el log
Get-Content C:\dtcore\logs\backup.log -Tail 20
```

---

## Configuración de rclone con Google Drive

Solo se hace una vez por instalación.

### 1. Iniciar el wizard interactivo

```powershell
C:\dtcore\tools\rclone.exe config
```

### 2. Seguir el wizard

```
n) New remote
name> gdrive
Storage> drive          # Google Drive
client_id>              # dejar vacío
client_secret>          # dejar vacío
scope> 1                # drive (acceso completo)
root_folder_id>         # dejar vacío
service_account_file>   # dejar vacío
Edit advanced config? n
Use web browser to authenticate? y
```

Rclone abrirá el browser automáticamente. Iniciar sesión con la cuenta de Google Drive del cliente y autorizar. El token se guarda en `%APPDATA%\rclone\rclone.conf`.

### 3. Verificar y crear la carpeta de destino

```powershell
C:\dtcore\tools\rclone.exe ls gdrive:
C:\dtcore\tools\rclone.exe mkdir gdrive:DTCore/backups
C:\dtcore\tools\rclone.exe ls gdrive:DTCore/backups
```

### 4. Prueba de backup manual

```powershell
powershell -File C:\dtcore\scripts\backup.ps1
C:\dtcore\tools\rclone.exe ls gdrive:DTCore/backups
```

---

## Smoke test post-instalación

Verificar estos 15 puntos antes de entregar el sistema al cliente:

1. `Get-Service postgresql-x64-16` → `Running`
2. `Get-Service dtcore-backend` → `Running`
3. `Get-Service dtcore-nginx` → `Running`
4. `psql -U dtcore_admin -d dtcore_db -h localhost -c "SELECT 1"` → `(1 row)`
5. `Invoke-WebRequest http://localhost:8000/health` → `{"status":"ok"}`
6. `Invoke-WebRequest https://localhost/api/health` → `{"status":"ok"}` (sin error de certificado)
7. Abrir `https://localhost` en Chrome/Edge → carga la pantalla de login sin advertencia de seguridad
8. Login con el usuario admin del seed → entra al dashboard
9. Crear un producto de prueba → aparece en el listado
10. Crear una venta de prueba → stock se actualiza
11. Desde un dispositivo del cliente en la misma red WiFi: abrir `https://<ip-lan>` → carga la app
12. Ejecutar `powershell -File C:\dtcore\scripts\backup.ps1` → log termina con "Backup completado OK"
13. Verificar que el archivo `.zip` aparece en `C:\dtcore\backups\`
14. Verificar que el archivo aparece en Google Drive en `DTCore/backups/`
15. Reiniciar la PC-servidor → todos los servicios arrancan solos (verificar con `Get-Service`)

---

## Monitoreo de logs

```powershell
# Backend
Get-Content C:\dtcore\logs\backend.log -Tail 50 -Wait

# Nginx
Get-Content C:\dtcore\logs\nginx.log -Tail 50

# Backups
Get-Content C:\dtcore\logs\backup.log -Tail 30

# Estado de servicios
Get-Service | Where-Object { $_.Name -like "*dtcore*" -or $_.Name -like "postgresql*" }
```

---

## Procedimiento de actualizaciones

Antes de actualizar, identificar qué archivos cambiaron para saber qué pasos son necesarios:

```powershell
cd C:\dtcore
git fetch
git log HEAD..origin/main --oneline          # commits nuevos
git diff HEAD..origin/main --name-only       # archivos que cambian
```

### Tabla de decisión

| Qué cambió                                             | Pasos requeridos                                                                   |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Solo frontend (`.tsx`, `.ts`, `.css`)                  | git pull → rebuild frontend → reload nginx                                         |
| Solo backend `.py` sin migraciones ni seed             | git pull → restart backend                                                         |
| Backend `.py` con nuevas migraciones Alembic           | git pull → stop backend → `pip install` → `alembic upgrade head` → start backend   |
| Backend `.py` con nuevos paquetes (`requirements.txt`) | git pull → stop backend → `pip install -r requirements.txt` → start backend        |
| **Nuevo setting en seed** (`seed/settings.py`)         | git pull → stop backend → `pip install` → `python -m app.seed.run` → start backend |
| Frontend + backend combinado                           | todos los pasos anteriores que apliquen                                            |

> **Cómo distinguir "migraciones" de "seed":** una migración Alembic agrega/modifica columnas o tablas (archivos en `alembic/versions/`). Un seed agrega filas de configuración a tablas existentes (archivos en `app/seed/`). Ambos pueden aparecer en el mismo update — correr ambos si es el caso.

---

### Paso 0 — Bajar cambios (siempre)

```powershell
cd C:\dtcore
git pull
```

---

### Paso 1 — Backend con cambios en `.py`

```powershell
cd C:\dtcore\tools
.\nssm.exe stop dtcore-backend
```

**Si `requirements.txt` cambió** (nuevo paquete):

```powershell
cd C:\dtcore\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Si hay nuevas migraciones Alembic** (archivos nuevos en `alembic/versions/`):

```powershell
cd C:\dtcore\backend
.venv\Scripts\Activate.ps1
alembic upgrade head
```

**Si hay nuevos settings en el seed** (cambios en `app/seed/settings.py` u otros archivos de `app/seed/`):

```powershell
cd C:\dtcore\backend
.venv\Scripts\Activate.ps1
python -m app.seed.run
```

El seed usa `ON CONFLICT DO NOTHING` — es seguro correrlo siempre, no sobrescribe datos existentes. Ante la duda, correrlo.

Reiniciar el backend:

```powershell
cd C:\dtcore\tools
.\nssm.exe start dtcore-backend
```

---

### Paso 2 — Frontend con cambios en `.tsx`, `.ts`, `.css`

```powershell
cd C:\dtcore\frontend
npm install
npm run build
C:\dtcore\nginx\nginx.exe -s reload
```

---

### Verificación post-update

```powershell
cd C:\dtcore\tools
.\nssm.exe status dtcore-backend   # SERVICE_RUNNING
.\nssm.exe status dtcore-nginx     # SERVICE_RUNNING
```

En el browser:

1. Abrir `https://localhost` → carga el login
2. Login con admin → entra al dashboard
3. Verificar la funcionalidad modificada

Hacer smoke test completo (puntos 5–10 de la lista de instalación) si el update involucró migraciones o cambios en flujos críticos (POS, compras, stock).

---

## Plan de rollback

### Rollback de código

```powershell
cd C:\dtcore
git log --oneline -10          # identificar el commit previo estable
git checkout <commit-hash>     # o git reset --hard <commit-hash> si ya se confirmó el estado

# Rebuild y reinicio (igual que actualizaciones, desde el paso 2)
```

Si hubo migraciones de Alembic en el update:

```powershell
cd C:\dtcore\backend
.venv\Scripts\Activate.ps1
alembic downgrade -1           # bajar una revisión
# o alembic downgrade <revision-id> para bajar a un punto específico
```

### Rollback desde backup (pérdida de datos)

```powershell
# 1. Detener el backend para evitar escrituras durante la restauración
cd C:\dtcore\tools
.\nssm.exe stop dtcore-backend

# 2. Identificar el backup a restaurar
Get-ChildItem C:\dtcore\backups\                         # backups locales
C:\dtcore\tools\rclone.exe ls gdrive:DTCore/backups      # backups en Drive

# 3. Si el backup está en Drive, descargarlo
C:\dtcore\tools\rclone.exe copy "gdrive:DTCore/backups\dtcore_20260101_020000.zip" C:\dtcore\backups\

# 4. Descomprimir
Expand-Archive -Path C:\dtcore\backups\dtcore_20260101_020000.zip -DestinationPath C:\dtcore\backups\

# 5. Restaurar en PostgreSQL
$env:PGPASSWORD = (Get-Content C:\dtcore\scripts\.pgcreds -Raw).Trim()
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U dtcore_admin -h localhost -d postgres `
    -c "DROP DATABASE dtcore_db; CREATE DATABASE dtcore_db OWNER dtcore_admin;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U dtcore_admin -h localhost -d dtcore_db `
    -f C:\dtcore\backups\dtcore_20260101_020000.sql

# 6. Reiniciar el backend
cd C:\dtcore\tools
.\nssm.exe start dtcore-backend
```

### Restauración en PC nueva (desastre total)

1. Instalar todos los pre-requisitos (ver tabla inicial)
2. Clonar el repo: `git clone https://github.com/crgiocolman/dtcore.git C:\dtcore`
3. Recrear `.env` con las credenciales del cliente
4. Ejecutar instalación completa (secciones PostgreSQL → Backend → Frontend → NSSM)
5. Configurar rclone con la cuenta de Drive del cliente
6. Descargar el último backup desde Drive y restaurar (ver pasos 3-6 del rollback anterior)
7. Verificar con smoke test completo

---

## Troubleshooting

**El servicio dtcore-backend no arranca**
→ Revisar `C:\dtcore\logs\backend.log`. Causas comunes: `.env` no encontrado, `DATABASE_URL` incorrecta, puerto 8000 ocupado por otro proceso (`netstat -ano | findstr :8000`).

**Error de activación del venv en PowerShell**
→ Ejecutar `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` y reintentar.

**nginx falla al arrancar**
→ Verificar con `C:\dtcore\nginx\nginx.exe -t`. Causas comunes: rutas de certificados incorrectas, puerto 443 o 80 ocupado (`netstat -ano | findstr :443`). IIS puede ocupar el 80 — desactivarlo desde "Activar o desactivar características de Windows".

**Error de certificado en el browser**
→ La CA de mkcert no está instalada en el dispositivo. Ejecutar `mkcert -install` en la PC-servidor o importar `rootCA.pem` en el dispositivo cliente.

**`pg_dump` en el script de backup no encuentra la contraseña**
→ Verificar que el archivo `C:\dtcore\scripts\.pgcreds` existe y contiene la contraseña de `dtcore_admin` sin espacios ni saltos de línea extra. Probar con `Get-Content C:\dtcore\scripts\.pgcreds`. Si falta, crearlo nuevamente siguiendo la sección "Archivo de credenciales para backup".

**rclone falla con "token expired"**
→ Ejecutar `C:\dtcore\tools\rclone.exe config reconnect gdrive:` desde una sesión con acceso al browser.

**El backup corre pero no sube a Drive**
→ Verificar que `$remotePath` en `backup.ps1` coincide con el remote configurado en rclone (`gdrive:DTCore/backups`). Probar: `C:\dtcore\tools\rclone.exe ls gdrive:DTCore/backups`.

**Los servicios no arrancan después de reiniciar la PC**
→ Verificar en el Administrador de Servicios de Windows que `dtcore-backend`, `dtcore-nginx` y `postgresql-x64-16` tienen tipo de inicio "Automático". Si NSSM los muestra como `SERVICE_STOPPED`, revisar los logs de cada servicio.
