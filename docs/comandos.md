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

| Comando | Descripción |
|---|---|
| `pytest` | Corre todos los tests |
| `pytest -v` | Verbose |
| `pytest app/tests/services/test_stock_service.py` | Tests de un archivo específico |
| `pytest -k "cpp"` | Tests cuyo nombre contiene "cpp" |
| `pytest --cov=app --cov-report=html` | Coverage report en HTML |

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
