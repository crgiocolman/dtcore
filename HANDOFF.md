# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-05-28 — Fase 3 cerrada (productos + correcciones post-QA).

---

## Fase actual

**Fase 3 completa.** Próximo: **Fase 4 — Compras + Inventario inicial**, empezando por bloque 4.1 (Backend stock_movements + stock_current).

---

## Estado del diseño

Toda la documentación de diseño está cerrada. Los docs vivos son `HANDOFF.md` (este), `docs/common-patterns.md` (se llena reactivamente), y `docs/design-decisions.md` (se agrega al tomar decisiones nuevas).

---

## Estado del código

- Backend: 9 modelos, ~20 tablas, auth + settings + currencies + contacts + productos completos. 144+ tests, todos pasan.
- Frontend: layout con dark mode, auth con preservación de ruta tras F5, módulos completos de admin/settings, currencies, contacts, productos, categorías, unidades.
- Migraciones aplicadas hasta head actual. Ver `alembic current` para revisión vigente.

---

## Entorno local

```bash
# PostgreSQL
docker compose up -d

# Backend (en backend/)
.venv\Scripts\activate
uvicorn app.main:app --reload

# Frontend (en frontend/)
npm run dev   # → https://localhost:5173
```

Credenciales dev: `admin` / `admin123`. Container BD: `dtcore-db`, port 5432.

`.env` mínimo:

```
DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/dtcore_db
JWT_SECRET=<generar al instalar>
STORAGE_PATH=./storage
BACKUP_DRIVE_REMOTE_PATH=<configurar al desplegar>
```

---

## Próximo paso concreto

**Bloque 4.1 — Backend stock_movements + stock_current.** Es el corazón del sistema de stock: ledger append-only, lock pesimista, CPP. Plan mode obligatorio. Tests primero donde sea posible. Ver prompt en `docs/prompts.md`.

---

## Historial de fases

### Fase 3 — Productos (cerrada 2026-05-28)

Cubre catálogo de productos completo: categorías jerárquicas, productos con búsqueda fuzzy, unidades múltiples con factor de conversión, precios históricos append-only, catálogo normalizado de unidades de medida.

**Bloques principales:** 3.1 categorías → 3.2 productos backend (con `pg_trgm`) → 3.3 product_units con sus 6 reglas → 3.4 precios → 3.5/3.6/3.7 UIs → 3.8 catálogo de unidades (refactor de strings a FKs).

**Refactors importantes durante QA:**

- Toggle activo/inactivo para `product_units` (estado visible reversible, hard delete solo si no hay referencias). Ver `design-decisions.md`.
- Catálogo `units_catalog` reemplaza texto libre en `base_unit` / `unit_name`. Migración con backfill.
- Índices UNIQUE parciales (`WHERE deleted_at IS NULL`) en SKU, barcode, contactos, categorías. Ver `design-decisions.md`.
- Eliminado campo `is_active` de `products` — solo soft delete vía `deleted_at`. Endpoint `/restore` con validación de conflicto de SKU/barcode (409).
- JSON serializer custom en el engine para soportar UUID/datetime/Decimal en JSONB de audit_log. Ver `common-patterns.md`.

### Fase 2 — Contactos (cerrada 2026-05-26)

CRUD completo de contactos (clientes / proveedores / ambos), búsqueda por nombre o documento, paginación server-side, soft delete. PATCH semántico (no PUT). El filtro `contact_type=customer` incluye también `both` (y simétrico).

### Fase 1 — Panel admin + Settings (cerrada 2026-05-25)

Settings key-value tipadas con cache 60s, panel admin con secciones, gestión de monedas con exchange_rates editables solo si son la última y no usadas (ver `design-decisions.md`). Fixes de cierre: `apiFetch` retorna `undefined` en 204; UNIQUE de tasas como índice parcial; navegación F5 preserva ruta vía `RequireAuth` con estado loading.

### Fase 0 — Setup y fundaciones (cerrada 2026-05-25)

Estructura backend/frontend, Docker Compose con Postgres 16, Alembic async, schema completo (~20 tablas, 14 enums), seeds (admin, currencies, warehouse, settings), auth JWT con bcrypt, layout con dark mode + tokens semánticos, PWA + HTTPS con mkcert, scripts de backup/restore + cron + documentación de deployment.

---

## Documentación del proyecto

| Archivo                    | Para qué                             | Frecuencia de cambio |
| -------------------------- | ------------------------------------ | -------------------- |
| `CLAUDE.md`                | Reglas activas del proyecto          | Bajo                 |
| `HANDOFF.md` (este)        | Estado operativo actual              | Alto                 |
| `docs/erd.md`              | Modelo de datos detallado            | Bajo                 |
| `docs/roadmap.md`          | Fases y bloques                      | Bajo                 |
| `docs/prompts.md`          | Prompts por bloque para Claude Code  | Bajo                 |
| `docs/design-decisions.md` | Historial de por qué                 | Bajo                 |
| `docs/design-system.md`    | Sistema visual (tokens, componentes) | Bajo                 |
| `docs/common-patterns.md`  | Patrones de código                   | Medio                |
| `docs/comandos.md`         | Referencia de comandos               | Bajo                 |
| `docs/deployment.md`       | Guía de deployment y backups         | Bajo                 |

---

## Cómo retomar después de pausa

1. Leer este archivo
2. `git log --oneline -20` — últimos commits
3. `docker ps` + `alembic current` — entorno OK
4. Abrir Claude Code en la raíz del proyecto

---

## Tips operativos

**IP del contenedor BD desde host (Windows + bridge network):**

```powershell
docker network connect bridge dtcore-db
docker inspect dtcore-db | Select-String '"IPAddress"'
```

**Reset completo de BD para QA limpio:**

```bash
docker compose down -v
docker compose up -d
alembic upgrade head
python -m app.seed.run
```

---

## Cómo actualizar este archivo

Al cerrar un bloque o fase:

1. Actualizar "Próximo paso concreto"
2. Si cerraste una fase: agregar entrada concisa en "Historial de fases" (3-5 líneas, no enumerar cada archivo tocado — para eso está `git log`)
3. Actualizar la fecha de arriba

**Regla:** este archivo nunca debería pasar de ~120 líneas. Detalle granular va a `design-decisions.md` (porqués), `common-patterns.md` (patrones de código), o queda implícito en commits. Si te ves listando archivo por archivo, parate y resumí.
