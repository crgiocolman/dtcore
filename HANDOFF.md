# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-05-23 — Bloque 0.6 completado.

---

## Fase actual

**Fase 0 — Setup y fundaciones** (en progreso)

Próximo bloque a ejecutar: **0.7 — HTTPS local y PWA básica** (ver `docs/roadmap.md`).

---

## Estado del diseño

- ✅ Modelo de datos completo (`docs/erd.md`)
- ✅ Decisiones de diseño documentadas (`docs/design-decisions.md`)
- ✅ Reglas de proyecto (`CLAUDE.md`)
- ✅ Roadmap por fases (`docs/roadmap.md`)
- ✅ Prompts por bloque (`docs/prompts.md`)
- ✅ Base de SQLAlchemy + Alembic configurada (`app/database.py`, `app/config.py`, `app/models/mixins.py`, `app/enums.py`, Alembic async)
- ✅ Schema completo en BD — 20 tablas, 14 enums, migración `db0d114b5777` verificada (upgrade + downgrade + upgrade limpios)

---

## Estado BD local

- `docker-compose.yml` creado. Correr `docker compose up -d` para iniciar PostgreSQL 16.
- Container: `dtcore-db`, DB: `dtcore_db`, user: `admin`, password: `admin123`, port: 5432.
- Sin migraciones todavía. Primera migración se genera en bloque 0.3.

---

## Variables de entorno (.env local)

A definir al iniciar bloque 0.1. Plantilla esperada:

```
DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/dtcore_db
JWT_SECRET=<generar al instalar>
STORAGE_PATH=./storage
BACKUP_DRIVE_REMOTE_PATH=<configurar al desplegar>
```

---

## Arranque del entorno local

```bash
# PostgreSQL
docker compose up -d

# Backend (en backend/)
.venv\Scripts\activate
pip install -r requirements.txt

# Frontend (en frontend/)
npm run dev   # → https://localhost:5173
```

---

## Próximo paso concreto

Iniciar **Fase 0, bloque 0.6 — Layout y navegación**.

---

## Historial de fases cerradas

### Bloque 0.6 — Layout y navegación (2026-05-23)

- `tailwind.config.js`: paleta extendida — `primary` (blue), `secondary` (slate), `danger` (red), `success` (green)
- `frontend/src/components/AppLayout.tsx`: header full-width (logo DTCore + business_name + usuario + logout) + sidebar fijo + `<Outlet />` para rutas anidadas
- `frontend/src/components/Sidebar.tsx`: NavLink activo resaltado con `bg-primary-50 text-primary-700`; links: Inicio, POS, Ventas, Compras, Productos, Contactos, Inventario, Reportes, Admin
- `frontend/src/components/Placeholder.tsx`: componente genérico "En construcción" reutilizado por todas las rutas placeholder
- `frontend/src/features/settings/hooks/useSettings.ts`: retorna `businessName: 'DTCore'` hardcodeado — TODO Fase 1 bloque 1.2 cuando exista `GET /api/v1/settings/business_name`
- `frontend/src/features/admin/pages/Settings.tsx`: placeholder de configuración (implementación en Fase 1)
- `frontend/src/App.tsx`: React Router v6 con layout route pathless — `RequireAuth` wrapping `AppLayout` como padre de todas las rutas protegidas; rutas: `/`, `/pos`, `/ventas`, `/compras`, `/productos`, `/contactos`, `/inventario`, `/reportes`, `/admin/settings`

### Bloque 0.5 — Auth backend + frontend (2026-05-23)

- `backend/main.py`: FastAPI app con CORS (localhost:5173)
- `app/schemas/auth.py`: `LoginRequest`, `UserOut`, `TokenResponse`
- `app/services/auth_service.py`: `hash_password`, `verify_password`, `create_access_token`, `decode_token`, `authenticate_user`
- `app/api/deps.py`: `get_current_user` (valida JWT del header `Authorization`), `require_role(*roles)`
- `app/api/auth.py`: `POST /api/v1/auth/login`, `GET /me`, `POST /logout`
- `frontend/src/lib/api.ts`: `apiFetch<T>` con header automático + manejo de 401
- `frontend/src/features/auth/store.ts`: Zustand store con persistencia en localStorage (`dtcore_token`, `dtcore_user`)
- `frontend/src/features/auth/hooks/useAuth.ts`: hook que hidrata desde storage en primer render
- `frontend/src/features/auth/pages/Login.tsx`: formulario usuario/contraseña con manejo de error
- `frontend/src/components/RequireAuth.tsx`: redirect a `/login` si no autenticado
- `frontend/src/App.tsx`: React Router v6 con rutas pública (`/login`) y protegida (`/`)
- `frontend/vite.config.ts`: proxy `/api → http://localhost:8000`
- `backend/.env`: `SEED_ADMIN_PASSWORD=admin123` agregado para dev
- Nota: seed es idempotente (`ON CONFLICT DO NOTHING`); contraseña admin en dev es `admin123`



### Bloque 0.4 — Seeds iniciales (2026-05-23)

- `app/seed/currencies.py`: PYG, USD, BRL, ARS
- `app/seed/users.py`: admin con UUID fijo `00000000-0000-4000-8000-000000000001`; password vía `SEED_ADMIN_PASSWORD` env var o `getpass`
- `app/seed/warehouses.py`: "Depósito principal" con UUID fijo `00000000-0000-4000-8000-000000000002`, `is_default=true`
- `app/seed/settings.py`: 8 keys del ERD sección 1.2; `default_warehouse_id` apunta al UUID fijo del depósito
- `app/seed/run.py`: punto de entrada `python -m app.seed.run` (requiere `SEED_ADMIN_PASSWORD` en env o prompt)
- Todos idempotentes con `INSERT ... ON CONFLICT DO NOTHING`
- Verificado: primera y segunda ejecución limpias sin duplicados

### Bloque 0.3 — Schema completo (migración inicial) (2026-05-23)

- 14 enums Python en `app/enums.py`
- 20 tablas en 9 archivos de modelo (`app/models/`): users, settings, currencies, contacts, products, inventory, purchases, sales, audit
- Todos los FKs, unique constraints, check constraints e índices con nombres explícitos
- Partial indexes (barcode, document_number, uq_warehouses_one_default) correctos en migración
- Migración `db0d114b5777_initial_schema.py` generada con autogenerate + DROP TYPE agregados manualmente en downgrade
- Verificación: `upgrade head` → `downgrade base` → `upgrade head` limpios
- La BD queda en `head` (migración aplicada)

### Bloque 0.2 — Base de SQLAlchemy + Alembic + settings (2026-05-23)

- `app/config.py`: pydantic-settings con DATABASE_URL, JWT_SECRET, JWT_EXPIRES_HOURS (default 8), STORAGE_PATH, BACKUP_DRIVE_REMOTE_PATH
- `app/database.py`: `Base` declarativa, engine async (asyncpg), `AsyncSessionLocal`, `get_db()` dependency
- `app/models/mixins.py`: `TimestampMixin`, `SoftDeleteMixin`, `AuditUserMixin` (con `declared_attr` y FK names explícitos)
- `app/enums.py`: archivo listo para importar enums en bloque 0.3
- Alembic: `alembic.ini` + `alembic/env.py` configurado para async (`asyncio.run` + `async_engine_from_config`). DATABASE_URL se lee de `settings`, no de alembic.ini.
- `.env.example` en raíz del repo con instrucción de copiar a `backend/.env`
- Nota: para correr `alembic` hay que estar en `backend/` con el venv activado

### Bloque 0.1 — Estructura del proyecto (2026-05-23)

- Estructura `backend/` y `frontend/` creadas
- Docker Compose con PostgreSQL 16 (`dtcore-db`)
- Backend: `app/{api,services,models,schemas,seed,tests}/`, `requirements.txt`, `pyproject.toml` (ruff+black), venv Python
- Frontend: Vite 5 + React 18 + TS 5.5, Tailwind 3, React Router v6, Zustand, Recharts, vite-plugin-pwa, vite-plugin-mkcert
- Nota: Node 20.12.1 genera warnings EBADENGINE en eslint/globals; no afecta el dev server. Considerar actualizar Node a 20.19+ si genera problemas.

---

## Documentación del proyecto

| Archivo                    | Para qué                            | Frecuencia de cambio |
| -------------------------- | ----------------------------------- | -------------------- |
| `CLAUDE.md`                | Reglas activas del proyecto         | Bajo                 |
| `HANDOFF.md` (este)        | Estado operativo actual             | Alto                 |
| `docs/erd.md`              | Modelo de datos detallado           | Bajo                 |
| `docs/roadmap.md`          | Fases y bloques                     | Bajo                 |
| `docs/prompts.md`          | Prompts por bloque para Claude Code | Bajo                 |
| `docs/design-decisions.md` | Historial de por qué                | Bajo                 |
| `docs/common-patterns.md`  | Patrones de código                  | Medio                |
| `docs/comandos.md`         | Referencia de comandos              | Bajo                 |

---

## Cómo retomar después de pausa

1. Leer este archivo (HANDOFF.md) primero
2. `git log --oneline -20` para ver últimos commits
3. Verificar entorno local: `docker ps`, venv activado, `alembic current`
4. Abrir Claude Code en la raíz del proyecto

---

## Cómo obtener la ip del contenedor de la BD de docker

docker network connect bridge dtcore-db
docker inspect dtcore-db | Select-String '"IPAddress"'

---

## Cómo actualizar este archivo

Al cerrar un bloque o fase:

1. Mover el bloque/fase de "actual" a "cerrado" con fecha
2. Actualizar "Próximo paso concreto" al siguiente bloque
3. Agregar notas relevantes (decisiones que surgieron, fixes notables, deuda técnica)
4. Actualizar "Última actualización" arriba

Mantener el archivo conciso. Detalle largo va a otros docs (`design-decisions.md` para porqués, `common-patterns.md` para patrones).
