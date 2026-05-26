# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-05-26 — Bloque 3.3 cerrado. Próximo: 3.4 Backend precios.

---

## Fase actual

**Fase 3 — Productos**

Próximo bloque a ejecutar: **3.4 — Backend precios** (ver `docs/roadmap.md`).

---

## Estado del diseño

- ✅ Modelo de datos completo (`docs/erd.md`)
- ✅ Decisiones de diseño documentadas (`docs/design-decisions.md`)
- ✅ Reglas de proyecto (`CLAUDE.md`)
- ✅ Roadmap por fases (`docs/roadmap.md`)
- ✅ Prompts por bloque (`docs/prompts.md`)
- ✅ Sistema visual documentado (`docs/design-system.md`, `docs/common-patterns.md`)
- ✅ Base de SQLAlchemy + Alembic configurada
- ✅ Schema completo en BD — 20 tablas, 14 enums, migración `db0d114b5777` verificada
- ✅ Seeds iniciales: admin, currencies, warehouse, settings
- ✅ Auth JWT funcional (backend + frontend)
- ✅ Layout del frontend con dark mode + tokens semánticos
- ✅ PWA instalable con HTTPS local (mkcert + Workbox)
- ✅ Scripts de backup/restore + docs de deployment

---

## Estado BD local

- Container: `dtcore-db`, DB: `dtcore_db`, user: `admin`, password: `admin123`, port: 5432
- Migración `db0d114b5777_initial_schema.py` aplicada (head)
- Seeds ejecutados: admin (`admin123`), PYG/USD/BRL/ARS, "Depósito principal", 8 settings

---

## Variables de entorno (.env local)

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
uvicorn app.main:app --reload

# Frontend (en frontend/)
npm run dev   # → https://localhost:5173
```

---

## Próximo paso concreto

Iniciar **Fase 3, bloque 3.4 — Backend precios**.

---

## Historial de fases cerradas

### Bloque 3.3 — Backend unidades de producto (2026-05-26)

- `app/schemas/product_units.py`: `ProductUnitCreate` (id requerido, factor_to_base > 0), `ProductUnitUpdate` (todo opcional — incluye factor_to_base, inmutabilidad validada en service), `ProductUnitOut`.
- `app/services/product_unit_service.py`: 6 reglas de negocio implementadas y testeadas.
  - R1 (en `product_service.py`): `create_product` con `track_stock=True` crea automáticamente una `ProductUnit` con `unit_name=base_unit`, `factor_to_base=1`, ambas flags default=True.
  - R2: `delete_unit` rechaza si `factor_to_base == 1` → `ProductUnitBaseUnitDeleteError`.
  - R3: `delete_unit` rechaza si hay refs en `purchase_items`, `sale_items`, `stock_adjustment_items`, `product_prices` → `ProductUnitHasReferencesError`.
  - R4: `update_unit` rechaza cambio de `factor_to_base` si hay refs en las 4 tablas → `ProductUnitFactorImmutableError`. Si el nuevo valor == el actual, omite la verificación.
  - R5: `create_unit` y `update_unit` desmarcan el holder previo de `is_default_sale_unit` y `is_default_purchase_unit` antes de asignar la nueva unidad como default.
  - R6: `update_unit` rechaza si la unidad tiene `factor_to_base==1` y el update dejaría ambas flags default en False → `ProductUnitNoDefaultError`.
  - `_has_references`: helper que itera 4 tablas con `limit(1)`, corta al primer hit.
  - `_clear_default_flag`: helper que busca el holder actual de un flag y lo desactiva (excluye el unit_id propio en updates).
- `app/api/product_units.py`: `GET /{product_id}/units`, `POST /{product_id}/units` (201), `PATCH /{product_id}/units/{unit_id}`, `DELETE /{product_id}/units/{unit_id}` (204). Router verifica existencia del producto antes de delegar al service. `IntegrityError` → 409 (nombre duplicado).
- `main.py`: router `product_units_router` registrado en `/api/v1/products` (mismo prefix que productos, los paths incluyen `/{product_id}/units`).
- `app/tests/test_product_unit_service.py`: 27 tests — todos pasan. TestGetUnits, TestGetUnit, TestCreateUnit (Rule 5), TestUpdateUnit (Rules 4, 5, 6), TestDeleteUnit (Rules 2, 3).
- `app/tests/test_product_service.py` actualizado: `test_adds_product_and_audit_log_to_session` → `test_adds_product_base_unit_and_audit_log_to_session` (espera count=3); nuevo `test_no_base_unit_when_track_stock_false` (count=2).
- Suite completa: **114 tests, todos pasan**.

### Bloque 3.2 — Backend productos (2026-05-26)

- `alembic/versions/e4f5a6b7c8d9_enable_pg_trgm_and_gin_index.py`: habilita extensión `pg_trgm` + crea índice GIN `ix_products_name_trgm` sobre `products.name`. Head: `e4f5a6b7c8d9`. **Pendiente aplicar: `alembic upgrade head`**.
- `app/schemas/products.py`: `ProductCreate` (id requerido — UUID en cliente), `ProductUpdate` (todo opcional), `ProductOut` (con AuditUserMixin), `ProductListOut`, `ProductSearchResult` (incluye `similarity: float`).
- `app/services/product_service.py`: `get_product`, `list_products` (ILIKE + filtros categoria/is_active + paginación), `search_products` (trigram: SKU exacto o barcode primero, luego ILIKE en nombre con score `GREATEST(similarity, exact_match)`), `create_product`, `update_product`, `delete_product` (soft delete). Todas las mutaciones crean AuditLog.
- `app/api/products.py`: `GET /products/search` (declarado antes de `/{id}` para evitar routing conflict), `GET /products`, `GET /products/{id}`, `POST /products` (201), `PUT /products/{id}`, `DELETE /products/{id}` (204). `IntegrityError` → 409 "Ya existe un producto con ese SKU".
- `app/tests/test_product_service.py`: 20 tests — CRUD + search result mapping + cast a float. Todos pasan.
- `main.py`: router registrado en `/api/v1/products`.

### Bloque 3.1 — Backend categorías (2026-05-26)

- `app/schemas/categories.py`: `CategoryCreate` (id requerido — UUID en cliente), `CategoryUpdate` (todo opcional para PUT), `CategoryOut`, `CategoryTreeNode` (recursivo con `model_rebuild()`).
- `app/services/category_service.py`: `get_category`, `get_category_tree` (árbol O(n) en memoria), `create_category`, `update_category`, `delete_category` (soft delete). `_would_create_cycle` recorre la cadena de ancestros para detectar ciclos. Excepciones: `CategoryNotFoundError`, `CategoryParentNotFoundError`, `CategoryCycleError`.
- `app/api/categories.py`: `GET /categories` (árbol), `GET /categories/{id}`, `POST /categories` (201), `PUT /categories/{id}`, `DELETE /categories/{id}` (204). `IntegrityError` → 409 (nombre duplicado en mismo nivel). `CategoryCycleError` → 422.
- `main.py`: router registrado en `/api/v1/categories`.
- Sin migración: tabla `product_categories` ya existía en schema inicial.

### Fase 2 — Contactos (2026-05-26)

### Bloque 2.3 — UI formulario de contacto (2026-05-26)

- `src/features/contacts/pages/ContactForm.tsx`: componente único para `/contactos/nuevo` y `/contactos/:id`. `isEdit = Boolean(id)` desde `useParams`.
- 4 secciones en `card`: Identificación (tipo + documento), Datos del contacto (business_name requerido + trade_name), Comunicación (teléfono, email, dirección), Notas y estado (notas + toggle is_active).
- `DeleteModal` local con confirmación; `Toggle` local (no extraído a shared — sin abstracción prematura).
- Validaciones: `business_name` requerido, `document_number` requerido si `document_type !== 'none'`, regex de email. Cambiar `document_type` a `none` limpia el error y deshabilita el input.
- `document_number` enviado como `null` cuando `document_type === 'none'`.
- `crypto.randomUUID()` para UUID del contacto nuevo.
- Layout: `flex flex-col h-full` + `form flex-1 overflow-y-auto` + `max-w-2xl pb-6` (patrón formulario largo de `common-patterns.md`).
- `src/features/contacts/api/contacts.ts` extendido: interfaces `ContactCreate`, `ContactUpdate`; funciones `fetchContact`, `createContact`, `updateContact`, `deleteContact`.
- `App.tsx`: rutas `/contactos/nuevo` y `/contactos/:id` apuntando a `ContactForm`.
- `tsc --noEmit` pasa sin errores.

### Bloque 2.2 — UI lista de contactos (2026-05-26)

- `src/features/contacts/hooks/useContacts.ts`: estado de lista encapsulado (data, loading, error, page, search, contactType). Debounce de 300ms; resetea page a 1 al cambiar filtros.
- `src/features/contacts/pages/ContactsList.tsx`: tabla con columnas nombre, documento (con prefijo de tipo), tipo (badge coloreado), teléfono, email, estado. Búsqueda con ícono Search, select de tipo. Paginación server-side con ChevronLeft/Right. Estado vacío con ícono Users y botón condicional "Agregar primer contacto".
- `src/features/contacts/api/contacts.ts` (versión inicial): tipos `ContactType`, `DocumentType`, interfaces `ContactOut`, `ContactListOut`, `ContactListParams`; `fetchContacts`.
- `App.tsx`: ruta `/contactos` apuntando a `ContactsList`. Fila clickeable navega a `/contactos/:id`.

### Bloque 2.1 — Backend contactos (2026-05-26)

- `app/models/contacts.py`: modelo `Contact` con `SoftDeleteMixin` + `AuditUserMixin`. Enum `ContactType` (customer/supplier/both), `DocumentType` (ruc/ci/passport/none). Índice en `business_name` + `document_number`.
- `app/schemas/contacts.py`: `ContactOut`, `ContactCreate` (id requerido — UUID en cliente), `ContactUpdate` (todo opcional para PATCH), `ContactListOut` (con `total_pages`).
- `app/services/contact_service.py`: `list_contacts` filtra `deleted_at IS NULL`; contactos de tipo `customer`/`supplier` incluyen los de tipo `both` (filtro `IN([type, BOTH])`); búsqueda por `business_name` o `document_number` (ILIKE). `create_contact`, `get_contact`, `update_contact`, `delete_contact` (soft delete). Audit log en todas las mutaciones.
- `app/api/contacts.py`: endpoints `GET /contacts`, `GET /contacts/{id}`, `POST /contacts` (201), `PATCH /contacts/{id}`, `DELETE /contacts/{id}` (204). Commit/rollback en router.
- `app/main.py`: router registrado en `/api/v1/contacts`.
- Migración no requerida (tabla `contacts` ya existía en schema inicial).

---

### Fixes de cierre Fase 1 (2026-05-25)

Cuatro bugs corregidos después de prueba manual del bloque 1.4b:

- **`apiFetch` + 204**: `res.json()` fallaba en respuestas vacías (DELETE devuelve 204). Fix: retornar `undefined as T` si `res.status === 204` en `src/lib/api.ts`.
- **UniqueConstraint + soft delete**: la constraint `UNIQUE(currency_code, effective_date)` bloqueaba reinsertar una tasa con la misma fecha después de eliminarla (el registro soft-deleted seguía ocupando la key). Fix: reemplazada por partial unique index `WHERE deleted_at IS NULL` — migración `b46762debd86`.
- **`can_edit` al agregar tasa**: `handleRateSaved` insertaba la nueva tasa con `can_edit: false` (valor por defecto del backend) sin actualizar el flag de las existentes. Fix: si la nueva tasa queda en posición 0 tras el sort, se recalcula `can_edit` para toda la lista (`i === 0` → true, resto → false).
- **`can_edit` al eliminar tasa**: `handleRateDeleted` filtraba el array local, pero la nueva tasa en posición 0 conservaba `can_edit: false`. Fix: invalidar la key en `ratesMap` en lugar de filtrar — el `useEffect` existente hace refetch y el servidor devuelve los flags correctos.
- **Navegación F5 en rutas protegidas**: `RequireAuth` redirigía a `/login` durante el primer render (antes de que `initFromStorage` corriera en el `useEffect`). Fix:
  - `AuthStore`: campo `isLoading: true` por defecto; `initFromStorage` ahora async — llama a `GET /api/v1/auth/me` para validar el token, setea `isLoading: false` al terminar (éxito o error).
  - `RequireAuth`: muestra spinner mientras `isLoading`; al redirigir a `/login` incluye `state={{ from: location }}`.
  - `Login`: lee `location.state.from.pathname` y navega ahí post-login (fallback a `/`).

### Bloque 1.4b — Edición y eliminación de tasas de cambio (2026-05-25)

- Migración `62cdf51dca49`: ADD COLUMN `deleted_at TIMESTAMPTZ NULL` en `exchange_rates`.
- `ExchangeRate` ahora hereda `SoftDeleteMixin` — soft delete via `deleted_at`.
- `currencies_service.py`: excepciones `ExchangeRateNotFoundError`, `ExchangeRateNotLatestError`, `ExchangeRateInUseError`; funciones `get_exchange_rate`, `can_edit_or_delete`, `update_exchange_rate`, `delete_exchange_rate`; `_assert_editable` verifica max `effective_date` + ausencia de purchases/sales con `created_at > rate.created_at`.
- `get_exchange_rates` filtra `deleted_at IS NULL`.
- `ExchangeRateOut` tiene campo `can_edit: bool = False`. Nuevo schema `ExchangeRatePatch`.
- `list_rates` calcula `can_edit` solo para la tasa más reciente (O(1) extra queries).
- `api/exchange_rates.py`: `PATCH /api/v1/exchange-rates/{id}` y `DELETE /api/v1/exchange-rates/{id}`, ambos mapean `ExchangeRateNotLatestError`/`ExchangeRateInUseError` → HTTP 409 con mensaje en español.
- `Currencies.tsx`: columna "Acciones" en tabla con botones Pencil/Trash2 (visibles solo si `can_edit`, `invisible` en las demás filas para mantener layout). Modales `EditRateModal` (edita `rate_to_base` + `notes`, muestra `currency_code` y `effective_date` como texto) y `DeleteRateModal` (confirmación con `.btn-danger`). Toast de error muestra `.detail` del backend.
- 8 tests en `test_currencies_service.py` — todos pasan sin BD real.
- Fix previo en misma sesión: `MissingGreenlet` en `patch_currency` y `create_rate` — corregido con `await db.refresh(...)` post-commit.

### Bloque 1.4 — UI gestión de monedas (2026-05-25)

- `app/schemas/currencies.py`: `CurrencyOut`, `CurrencyPatch`, `ExchangeRateOut`, `ExchangeRateCreate`.
- `app/services/currencies_service.py`: `get_all_currencies`, `get_currency`, `toggle_currency`, `get_exchange_rates`, `create_exchange_rate`.
- `app/api/currencies.py`: `GET /api/v1/currencies`, `PATCH /api/v1/currencies/{code}` (admin), `GET /api/v1/currencies/{code}/rates`, `POST /api/v1/currencies/{code}/rates` (admin, 409 en fecha duplicada).
- `main.py`: router currencies registrado en `/api/v1/currencies`.
- `src/features/admin/api/currencies.ts`: `fetchCurrencies`, `toggleCurrency`, `fetchExchangeRates`, `createExchangeRate`.
- `src/features/admin/pages/Currencies.tsx`: layout two-column — lista de monedas (cards con toggle) + panel de tipos de cambio históricos. Modal para nueva tasa (rate + fecha + notas). Cache de rates por moneda. Toggle deshabilitado para PYG (moneda base). Toast de éxito/error.
- `App.tsx`: ruta `/admin/currencies` agregada.
- `Sidebar.tsx`: "Admin" → "Configuración", agregado "Monedas" con icono `Coins`.
- `crypto.randomUUID()` en el frontend para el ID del exchange_rate.
- TS y backend importan limpio.

### Bloque 1.3 — UI panel admin (2026-05-25)

- `src/features/admin/api/settings.ts`: `fetchAllSettings()` y `updateSetting(key, value)` usando `apiFetch`.
- `src/features/admin/pages/Settings.tsx`: página `/admin/settings` con formulario agrupado en 4 secciones (Negocio, Moneda, Ventas, Stock). Un botón "Guardar" por sección. Input apropiado por `value_type`: `text`/`number`/`checkbox`/`textarea`. `default_warehouse_id` oculto (no editable hasta que haya UI de depósitos). Toast inline al guardar (éxito o error con detalle del backend).
- `src/features/settings/hooks/useSettings.ts`: reemplazado el hardcode por fetch real a `GET /api/v1/settings/business_name`. Fallback a 'DTCore' si falla.
- TypeScript compila sin errores (`npx tsc --noEmit`).

### Bloque 1.2 — API de settings (2026-05-25)

- `app/schemas/settings.py`: `SettingOut` (key, value_type, value parseado, description, updated_at, updated_by_user_id) + `SettingUpdateRequest` (value: Any).
- `app/api/settings.py`: `GET /api/v1/settings` (requiere auth), `GET /api/v1/settings/{key}` (requiere auth), `PUT /api/v1/settings/{key}` (requiere rol admin). 404 en key inexistente, 422 en tipo incompatible, 500 en fallo de BD.
- `settings_service.py` extendido: `get_setting_row`, `get_all_setting_rows`, `parse_value` (alias público de `_parse_value`), y `set_setting` ahora setea `updated_at` explícitamente en Python para que el response refleje el valor correcto sin necesidad de refresh post-commit.
- `main.py`: router settings registrado en `/api/v1/settings`.

### Bloque 1.1 — Service de settings (2026-05-25)

- `app/services/settings_service.py`: `get_setting(db, key)`, `set_setting(db, key, value, user_id)`, `get_all_settings(db)`.
- Parseo tipado via `_parse_value` y serialización via `_serialize_value` para los 5 `value_type` (`string`, `int`, `decimal`, `bool`, `json`). Todos los errores normalizados a `ValueError`.
- Cache en memoria (`_cache` + `_cache_time`) con TTL de 60s e invalidación explícita al escribir. Cache es module-level; válido para deploy single-process uvicorn.
- El router es responsable del `db.commit()` / `db.rollback()` — el service solo modifica el objeto ORM.
- 49 tests en `app/tests/test_settings_service.py`: parseo, serialización, roundtrips, cache TTL, cache invalidation, validación de tipos, KeyError en keys inexistentes. Todos pasan sin BD real (AsyncMock).

---

### Bloque 0.8 — Backups (2026-05-25)

- `scripts/backup.sh`: pg_dump del contenedor + gzip + rclone copy a Drive + limpieza local >30 días. Configurable via `.env` (`DB_CONTAINER`, `DB_USER`, `DB_NAME`, `BACKUP_LOCAL_DIR`, `BACKUP_DRIVE_REMOTE_PATH`, `RETENTION_DAYS_LOCAL`).
- `scripts/verify_backup.sh`: verifica que existe dump de ayer en local; si no, escribe en `scripts/logs/verify_errors.log` y sale con exit 1 (detectable por cron).
- `scripts/restore.sh`: toma `<archivo.sql.gz>`, pide confirmación interactiva, termina conexiones activas, drop+recreate DB, restaura.
- `scripts/logs/.gitkeep`: directorio trackeado; los `.log` en `.gitignore`.
- `docs/deployment.md`: pre-requisitos, `rclone config` paso a paso, crontab diario (2 AM backup + 7 AM verify), 3 casos de restore (local / desde Drive / PC nueva), troubleshooting.
- `.gitignore`: agregados `backups/` y `scripts/logs/*.log`.

### Bloque 0.7 — HTTPS local y PWA básica (2026-05-25)

- `vite-plugin-mkcert` + `vite-plugin-pwa` ya instalados desde bloque 0.1; este bloque los configuró correctamente.
- `vite.config.ts`: `strategies: 'generateSW'`, manifest completo (`name`, `short_name`, `description`, `theme_color: #111A2E`, `background_color: #0B1220`, `display: standalone`, iconos 192/512/512-maskable), Workbox con `cleanupOutdatedCaches`, `clientsClaim`, `skipWaiting`.
- `public/icons/icon-192.png` y `icon-512.png`: placeholders PNG sólidos en color `bg-surface` (#111A2E). Reemplazar con iconos reales en Fase 7.
- Build verificado: genera `dist/sw.js`, `dist/workbox-*.js`, `dist/manifest.webmanifest`, 12 entries precacheados.
- `docs/comandos.md`: sección "HTTPS local con mkcert — instalar CA root en Android" con pasos para iOS también.
- Nota: `npm run build` da errores de tsconfig (`erasableSyntaxOnly`, `tsBuildInfoFile`) pre-existentes del template de Vite. `npx vite build` y `npx tsc --noEmit` corren limpio. No bloquean el funcionamiento.

### Sistema visual (2026-05-24, extensión del bloque 0.6)

- `tailwind.config.js`: tokens semánticos via CSS variables (`bg/*`, `border/*`, `text/*`, paletas `primary`/`accent`/`danger`/`success`/`warning`/`info`, `fontFamily.sans: Inter`, `borderRadius.DEFAULT: 6px`, `darkMode: 'class'`).
- `src/index.css`: Google Fonts Inter, CSS variables dark mode con fondos azulados (`bg-base: #0B1220`, `bg-surface: #111A2E`, etc.), clases `@layer components` (`.btn-primary`, `.btn-accent`, `.btn-secondary`, `.btn-danger`, `.btn-ghost`, `.input`, `.label`, `.card`).
- AppLayout, Sidebar, Placeholder, Login refactorizados a tokens semánticos; sin `gray-*`/`slate-*`/`text-white` directos.
- `docs/design-system.md`: creado como fuente de verdad visual.
- `docs/common-patterns.md`: sección "Sistema visual" agregada.

### Bloque 0.6 — Layout y navegación (2026-05-23)

- `src/components/AppLayout.tsx`: header (logo + business_name + usuario + logout con icono `LogOut`) + sidebar + `<Outlet />`
- `src/components/Sidebar.tsx`: 9 NavLinks con iconos Lucide (`Home`, `ShoppingCart`, `Receipt`, `Truck`, `Package`, `Users`, `Boxes`, `BarChart3`, `Settings`), activo con `bg-primary-500/10 text-primary-500`
- `src/components/Placeholder.tsx`: componente "En construcción" reutilizable
- `src/features/settings/hooks/useSettings.ts`: `businessName: 'DTCore'` hardcodeado — reemplazar en bloque 1.2
- `src/features/admin/pages/Settings.tsx`: placeholder (implementar en Fase 1)
- `src/App.tsx`: layout route pathless — `RequireAuth > AppLayout` como padre; rutas: `/`, `/pos`, `/ventas`, `/compras`, `/productos`, `/contactos`, `/inventario`, `/reportes`, `/admin/settings`
- `lucide-react` instalado

### Bloque 0.5 — Auth backend + frontend (2026-05-23)

- `app/api/auth.py`: `POST /api/v1/auth/login`, `GET /me`, `POST /logout`
- `app/services/auth_service.py`: bcrypt cost 12, JWT con expiración configurable
- `app/api/deps.py`: `get_current_user`, `require_role(*roles)`
- `frontend/src/lib/api.ts`: `apiFetch<T>` con header automático + manejo de 401
- `frontend/src/features/auth/store.ts`: Zustand con persistencia en localStorage (`dtcore_token`, `dtcore_user`)
- `frontend/src/features/auth/hooks/useAuth.ts`: hidrata desde storage en primer render
- `frontend/src/features/auth/pages/Login.tsx`: formulario con manejo de error
- `frontend/src/components/RequireAuth.tsx`: redirect a `/login` si no autenticado
- Contraseña admin en dev: `admin123`

### Bloque 0.4 — Seeds iniciales (2026-05-23)

- `app/seed/`: `currencies.py`, `users.py`, `warehouses.py`, `settings.py`, `run.py`
- Admin UUID fijo `00000000-0000-4000-8000-000000000001`; password vía `SEED_ADMIN_PASSWORD` env var o prompt
- Warehouse "Depósito principal" UUID fijo `00000000-0000-4000-8000-000000000002`, `is_default=true`
- 8 settings keys del ERD. Todos idempotentes (`INSERT ... ON CONFLICT DO NOTHING`)

### Bloque 0.3 — Schema completo (2026-05-23)

- 14 enums Python en `app/enums.py`, 20 tablas en 9 archivos de modelo
- Migración `db0d114b5777_initial_schema.py`: upgrade/downgrade/upgrade verificados
- Partial indexes, CHECK constraints, FK names explícitos según convención

### Bloque 0.2 — Base de SQLAlchemy + Alembic (2026-05-23)

- `app/config.py`: pydantic-settings
- `app/database.py`: engine async (asyncpg), `AsyncSessionLocal`, `get_db()`
- `app/models/mixins.py`: `TimestampMixin`, `SoftDeleteMixin`, `AuditUserMixin`
- Alembic configurado para async; DATABASE_URL desde settings

### Bloque 0.1 — Estructura del proyecto (2026-05-23)

- Estructura `backend/` y `frontend/`, Docker Compose con PostgreSQL 16
- Vite 5 + React 18 + TS 5.5, Tailwind 3, React Router v6, Zustand, Recharts
- Nota: Node 20.12.1 genera warnings EBADENGINE en eslint/globals — no afecta dev server

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
| `docs/design-system.md`    | Sistema visual (tokens, componentes)| Bajo                 |
| `docs/common-patterns.md`  | Patrones de código                  | Medio                |
| `docs/comandos.md`         | Referencia de comandos              | Bajo                 |
| `docs/deployment.md`       | Guía de deployment y backups        | Bajo                 |

---

## Cómo retomar después de pausa

1. Leer este archivo (HANDOFF.md) primero
2. `git log --oneline -20` para ver últimos commits
3. Verificar entorno: `docker ps`, venv activado, `alembic current`
4. Abrir Claude Code en la raíz del proyecto

---

## Cómo obtener la IP del contenedor de la BD de Docker

```powershell
docker network connect bridge dtcore-db
docker inspect dtcore-db | Select-String '"IPAddress"'
```

---

## Cómo actualizar este archivo

Al cerrar un bloque o fase:

1. Mover el bloque/fase de "actual" a "cerrado" con fecha
2. Actualizar "Próximo paso concreto" al siguiente bloque
3. Agregar notas relevantes (decisiones que surgieron, fixes notables, deuda técnica)
4. Actualizar "Última actualización" arriba

Mantener el archivo conciso. Detalle largo va a otros docs (`design-decisions.md` para porqués, `common-patterns.md` para patrones).
