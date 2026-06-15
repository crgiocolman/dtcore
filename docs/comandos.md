# docs/comandos.md — Comandos de referencia DTCore

Referencia rápida de comandos. Se completa a medida que el proyecto avanza.

---

## Entorno virtual (backend)

| Comando | Descripción |
|---|---|
| `python -m venv venv` | Crea el entorno virtual |
| `source venv/bin/activate` | Activa (Linux/Mac) |
| `venv\Scripts\activate` | Activa (Windows) |
| `deactivate` | Desactiva |

---

## Dependencias backend

| Comando | Descripción |
|---|---|
| `pip install -r requirements.txt` | Instala dependencias |
| `pip freeze > requirements.txt` | Regenera requirements |

---

## Servidor backend

| Comando | Descripción |
|---|---|
| `uvicorn app.main:app --reload` | FastAPI con recarga automática |
| `uvicorn app.main:app --reload --host 0.0.0.0` | Accesible desde otros dispositivos en la red local |
| `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Modo producción local |

---

## Docker (PostgreSQL)

| Comando | Descripción |
|---|---|
| `docker compose up -d` | Levanta PostgreSQL en background |
| `docker compose down` | Detiene contenedores |
| `docker compose logs -f db` | Logs de PostgreSQL en vivo |
| `docker ps` | Lista contenedores corriendo |

---

## PostgreSQL directo

| Comando | Descripción |
|---|---|
| `docker exec -it dtcore-db psql -U admin -d dtcore_db -c "\dt"` | Lista tablas |
| `docker exec -it dtcore-db psql -U admin -d dtcore_db` | Consola interactiva |
| `docker exec -it dtcore-db psql -U admin -d dtcore_db -c "\dT"` | Lista enums (tipos) |
| `docker exec dtcore-db pg_dump -U admin dtcore_db > backup.sql` | Dump rápido a archivo |

---

## Alembic

| Comando | Descripción |
|---|---|
| `alembic revision --autogenerate -m "descripcion"` | Genera migración |
| `alembic upgrade head` | Aplica migraciones pendientes |
| `alembic downgrade -1` | Revierte la última migración |
| `alembic current` | Migración actualmente aplicada |
| `alembic history` | Lista todas las migraciones |
| `alembic heads` | Lista heads (debería ser una sola) |

---

## Seed

| Comando | Descripción |
|---|---|
| `python -m app.seed.run` | Ejecuta todos los seeds |
| `python -m app.seed.run --only currencies` | Ejecuta solo un seed específico (si se implementa) |

---

## Tests backend

### Setup (una sola vez)

```bash
# Crear BD de tests (desde la PC o el contenedor de DB)
createdb -U admin dtcore_test
```

### Correr tests

| Comando | Descripción |
|---|---|
| `pytest` | Todos los tests (mocks + integración) |
| `pytest -v` | Verbose |
| `pytest app/tests/services/ app/tests/regressions/` | Solo integración (requiere dtcore_test) |
| `pytest app/tests/test_*.py` | Solo tests mock (rápidos, sin BD) |
| `pytest app/tests/regressions/` | Solo regresiones |
| `pytest app/tests/services/test_stock_service.py` | Archivo específico |
| `pytest -k "cpp"` | Tests cuyo nombre contiene "cpp" |
| `pytest -k "concurrent"` | Test de lock concurrente |
| `pytest --cov=app --cov-report=html` | Coverage report en HTML |

### Variables de entorno

Los tests de integración leen `DATABASE_URL` del entorno. Si no está seteada, `conftest.py`
aplica el default `postgresql+asyncpg://admin:admin123@localhost:5432/dtcore_test`.
Para usar otra URL: `DATABASE_URL=... pytest app/tests/services/`

---

## Frontend

| Comando | Descripción |
|---|---|
| `cd frontend && npm install` | Instala dependencias |
| `cd frontend && npm run dev` | Vite dev server (HMR) |
| `cd frontend && npm run build` | Build de producción |
| `cd frontend && npm run preview` | Sirve el build (para probar PWA real con SW) |
| `cd frontend && npm run lint` | Lint |

---

## Backup y restore

| Comando | Descripción |
|---|---|
| `./scripts/backup.sh` | Backup completo (pg_dump + rclone a Drive) |
| `./scripts/verify_backup.sh` | Verifica que existe dump del día anterior |
| `./scripts/restore.sh <archivo.sql>` | Restaura desde un dump local |

---

## Git

| Comando | Descripción |
|---|---|
| `git log --oneline -20` | Últimos 20 commits |
| `git status` | Estado actual |
| `git diff HEAD~1` | Diff contra commit anterior |

---

## Utilidades

| Comando | Descripción |
|---|---|
| `python scripts/recalculate_stock.py` | Reconstruye `stock_current` desde `stock_movements` (en caso de inconsistencia) |
| `python scripts/create_admin.py` | Crea un usuario admin nuevo (uso operativo, no para seed inicial) |

---

## HTTPS local con mkcert — instalar CA root en Android

Para que el service worker de la PWA se registre en el celular del cliente, el dispositivo tiene que confiar en el certificado local generado por mkcert. Sin este paso, el SW no instala y la app no aparece como "instalable".

### En la PC-servidor (una sola vez)

```bash
# Encontrar dónde mkcert guardó su CA root
mkcert -CAROOT
# → típicamente: /home/<usuario>/.local/share/mkcert/ (Linux)
#              o  C:\Users\<usuario>\AppData\Local\mkcert\ (Windows)

# El archivo que hay que copiar al celular es rootCA.pem
```

### En el celular Android

1. **Transferir el archivo `rootCA.pem` al celular** — por cable, WhatsApp, o servidor temporal:
   ```bash
   # Desde la PC: levantar servidor HTTP temporal (solo para la transferencia)
   cd $(mkcert -CAROOT) && python -m http.server 8080
   # En el celular: abrir http://<ip-pc>:8080/rootCA.pem y descargar
   ```

2. **Instalar el certificado en Android:**
   - Ir a `Ajustes → Seguridad → Más ajustes de seguridad → Instalar desde almacenamiento`
   - (En Android 14+: `Ajustes → Seguridad → Credenciales y certificados → Instalar certificado → Certificado de CA`)
   - Seleccionar el archivo `rootCA.pem` descargado
   - El sistema pedirá PIN/patrón para confirmar
   - Nombre sugerido: "DTCore Local CA"

3. **Verificar:**
   - Abrir Chrome en el celular
   - Ir a `https://<ip-de-la-pc>/`
   - No debería aparecer advertencia de certificado
   - Chrome mostrará el botón "Instalar app" o "Agregar a pantalla de inicio" (⋮ → Instalar app)

### Notas

- `mkcert` genera los certs en `vite-plugin-mkcert` automáticamente al correr `npm run dev`. Los certs quedan en `frontend/.vite-plugin-mkcert/`.
- Este procedimiento es **por dispositivo**. Si el cliente tiene varios celulares o notebooks, repetirlo en cada uno.
- El certificado de CA expira según la configuración de mkcert (por defecto: 10 años), no es necesario renovarlo frecuentemente.
- En iOS: descargar el `.pem` → `Ajustes → General → VPN y administración de dispositivos → Instalar perfil` → luego activarlo en `Ajustes → General → Info → Configuración de confianza de certificado`.

---

## Flujo típico al iniciar el día

```bash
# 1. Levantar PostgreSQL
docker compose up -d

# 2. Activar venv y backend
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
uvicorn app.main:app --reload

# 3. En otra terminal: frontend
cd frontend
npm run dev

# 4. (Opcional) Abrir Claude Code en la raíz
cd ..
claude
```
