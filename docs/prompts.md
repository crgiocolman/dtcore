# docs/prompts.md — Prompts para Claude Code

Prompts concisos por bloque. Claude Code tiene contexto completo en `CLAUDE.md`, `docs/erd.md`, `docs/design-decisions.md` y `docs/roadmap.md` — los prompts referencian esos docs en lugar de repetir su contenido.

## Cómo usar

1. Abrir Claude Code en la raíz del proyecto (`claude` en terminal)
2. Activar Plan Mode (`Shift + Tab`) si el bloque toca más de un archivo
3. Pegar el prompt del bloque correspondiente
4. Revisar el plan antes de aceptar; revisar diffs antes de aceptar cambios
5. Al cerrar el bloque: actualizar `HANDOFF.md`

## Convención

Todos los prompts asumen:

- Lectura previa de `CLAUDE.md`, `docs/erd.md`, `docs/roadmap.md`
- Para cualquier bloque que toque UI: lectura previa de `docs/design-system.md`
- Trabajo en plan mode para bloques que tocan múltiples archivos
- No commitear automáticamente (el usuario revisa y commitea manualmente)
- Si surge una decisión arquitectónica no resuelta, parar y consultar Claude.ai

---

# Fase 0 — Setup y fundaciones

### Bloque 0.1 — Estructura del proyecto

```
Implementar bloque 0.1 siguiendo docs/roadmap.md y CLAUDE.md.

Crear estructura inicial del proyecto DTCore:
- Carpetas backend/ y frontend/ con .gitignore apropiado
- README.md mínimo en la raíz
- docker-compose.yml con PostgreSQL 16 (servicio: db, container: dtcore-db, db: dtcore_db, user: admin)
- backend/: estructura de carpetas (app/api/, app/services/, app/models/, app/schemas/, app/seed/, app/tests/), requirements.txt con las dependencias del stack, venv, pyproject.toml con ruff y black configurados
- frontend/: scaffold Vite + React 18 + TypeScript, instalar Tailwind 3, React Router v6, Zustand, Recharts, Workbox/vite-plugin-pwa, vite-plugin-mkcert
- frontend/src/: estructura inicial (features/, components/, lib/, pages/)

No incluir todavía: modelos, migraciones, seeds, auth. Solo la estructura.

Plan mode obligatorio. Al final: instrucciones para verificar que docker compose up -d levanta la BD y que npm run dev arranca el frontend con HTTPS.
```

### Bloque 0.2 — Base de SQLAlchemy + Alembic + config

```
Implementar bloque 0.2 siguiendo docs/roadmap.md y CLAUDE.md.

- app/database.py: Base declarativa, engine async con asyncpg, session factory (get_db dependency)
- app/config.py: pydantic-settings con DATABASE_URL, JWT_SECRET, JWT_EXPIRES_HOURS, STORAGE_PATH
- app/models/mixins.py: TimestampMixin, SoftDeleteMixin, AuditUserMixin (ver docs/common-patterns.md)
- app/enums.py: archivo vacío con import de Enum listo
- Inicializar Alembic configurado para async (alembic.ini + alembic/env.py con async)
- .env.example en la raíz con las variables esperadas

No crear modelos todavía. Solo la base.
```

### Bloque 0.3 — Schema completo (migración inicial)

```
Implementar bloque 0.3 siguiendo docs/roadmap.md, CLAUDE.md y docs/erd.md.

Crear todos los modelos SQLAlchemy según docs/erd.md:
- Enums en app/enums.py (todos los enums del ERD)
- Modelos en app/models/ (un archivo por módulo: users.py, settings.py, currencies.py, contacts.py, products.py, inventory.py, purchases.py, sales.py, audit.py)
- Respetar todas las convenciones de CLAUDE.md: nombres explícitos de FK/unique/index, mixins, NUMERIC(18,4), etc.
- Generar la primera migración con alembic revision --autogenerate -m "initial schema"
- Revisar el archivo de migración: orden correcto de creación (ver docs/erd.md sección final), enums creados antes de tablas que los usan, downgrade limpio

Verificación al final: alembic upgrade head debe correr limpio en BD vacía, alembic downgrade base también.

Plan mode obligatorio. Este es un bloque grande — partir en sub-pasos si hace falta.
```

### Bloque 0.4 — Seeds iniciales

```
Implementar bloque 0.4 siguiendo docs/roadmap.md y docs/erd.md.

Crear seeds en app/seed/:
- app/seed/run.py: punto de entrada (python -m app.seed.run)
- app/seed/users.py: crea usuario admin (username/password configurables vía env vars o prompt seguro)
- app/seed/currencies.py: PYG (0 decimales, "Gs"), USD (2, "$"), BRL (2, "R$"), ARS (2, "$")
- app/seed/warehouses.py: crea "Depósito principal" con is_default=true
- app/seed/settings.py: todos los settings con sus defaults según docs/erd.md sección 1.2

Cada seed debe ser idempotente (no duplica si ya existe).
```

### Bloque 0.5 — Auth (backend + frontend)

```
Implementar bloque 0.5 siguiendo docs/roadmap.md y CLAUDE.md.

Backend:
- app/services/auth_service.py: hash_password (bcrypt cost 12), verify_password, create_access_token, decode_token
- app/api/auth.py: POST /api/v1/auth/login, GET /api/v1/auth/me, POST /api/v1/auth/logout
- app/api/deps.py: dependencia get_current_user que valida JWT del header Authorization
- Decorador/dependencia require_role(role) — definirla aunque no se use activamente en v1
- Schemas Pydantic en app/schemas/auth.py

Frontend:
- src/features/auth/: store Zustand (token, user, isAuthenticated), hook useAuth
- src/features/auth/pages/Login.tsx: formulario simple usuario+contraseña
- src/lib/api.ts: cliente fetch con interceptor que agrega Authorization header
- src/components/RequireAuth.tsx: wrapper que redirige a /login si no hay token

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.

Plan mode obligatorio.
```

### Bloque 0.6 — Layout del frontend

```
Implementar bloque 0.6 siguiendo docs/roadmap.md.

- src/components/AppLayout.tsx: header (logo "DTCore" + business_name desde settings + usuario logueado + botón logout) + sidebar de navegación + área de contenido
- src/components/Sidebar.tsx: links a todas las rutas placeholder (Inicio, POS, Ventas, Compras, Productos, Contactos, Inventario, Reportes, Admin)
- Rutas en App.tsx con React Router v6, cada una renderiza un componente placeholder "En construcción"
- src/features/admin/pages/Settings.tsx: placeholder (se implementa en Fase 1)
- Tema base de Tailwind: definir paleta (primario, secundario, danger, success) en tailwind.config.js
- Mostrar business_name desde un hook useSettings que consume GET /api/v1/settings/business_name (endpoint todavía no existe — leave un TODO o usar valor hardcodeado temporalmente y dejarlo marcado para resolver en Fase 1)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

### Bloque 0.7 — HTTPS local y PWA básica

```
Implementar bloque 0.7 siguiendo docs/roadmap.md.

- Configurar vite-plugin-mkcert en vite.config.ts
- Configurar vite-plugin-pwa con generateSW (Workbox)
- manifest.webmanifest: nombre "DTCore", short_name, descripción, theme_color, background_color, iconos (usar placeholders por ahora — 192x192 y 512x512)
- Verificar que npm run dev y npm run preview ambos sirven HTTPS
- Verificar que la app se puede instalar como PWA desde Chrome/Edge

Documentar en docs/comandos.md cómo importar el CA root de mkcert en celular Android para que el SW se registre.
```

### Bloque 0.8 — Backups

```
Implementar bloque 0.8 siguiendo docs/roadmap.md y docs/design-decisions.md (sección backups).

Crear en scripts/:
- backup.sh: pg_dump del contenedor + rclone copy a Drive (path configurable vía env var)
- verify_backup.sh: verifica que existe un dump del día anterior; si no, escribe a un log de errores
- restore.sh: restaura un dump local (toma archivo como argumento)

Documentar en docs/deployment.md (crear este archivo):
- Cómo configurar rclone inicialmente (rclone config con backend de Drive)
- Cómo configurar cron para backup diario (ej. 2 AM) y verificación semanal
- Cómo restaurar un backup en caso de desastre

Los scripts deben ser idempotentes y registrar logs en scripts/logs/.
```

---

# Fase 1 — Panel admin + Settings

### Bloque 1.1 — Service de settings

```
Implementar bloque 1.1 siguiendo docs/roadmap.md y docs/erd.md.

- app/services/settings_service.py:
  - get_setting(db, key) -> tipo apropiado según value_type
  - set_setting(db, key, value, user_id) -> valida tipo, actualiza updated_at/updated_by
  - get_all_settings(db) -> dict con todos los settings parseados
  - Cache en memoria con invalidación al escribir (TTL corto, ej. 60s, o invalidación explícita)
- Tests unitarios para parseo de cada value_type
```

### Bloque 1.2 — API de settings

```
Implementar bloque 1.2 siguiendo docs/roadmap.md.

- app/api/settings.py:
  - GET /api/v1/settings (lista todos, requiere auth)
  - GET /api/v1/settings/{key} (uno solo)
  - PUT /api/v1/settings/{key} (actualiza, requiere rol admin via require_role)
- Schemas Pydantic en app/schemas/settings.py
- Validación: el valor recibido debe ser compatible con el value_type del setting
```

### Bloque 1.3 — UI panel admin de settings

```
Implementar bloque 1.3 siguiendo docs/roadmap.md.

- src/features/admin/pages/Settings.tsx: formulario agrupado por sección (Negocio, Moneda, Ventas, Stock)
- Input según value_type (text/number/checkbox/textarea para json)
- Validación cliente + manejo de errores del backend
- Toast al guardar
- Hook useSettings actualizado para consumir /api/v1/settings correctamente

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

### Bloque 1.4 — UI gestión de monedas

```
Implementar bloque 1.4 siguiendo docs/roadmap.md y docs/erd.md.

Backend (si no se hizo en bloques anteriores):
- Endpoints CRUD básicos de currencies y exchange_rates en app/api/currencies.py

Frontend:
- src/features/admin/pages/Currencies.tsx: lista de monedas con toggle activar/desactivar
- Modal para cargar nuevo exchange_rate (currency + rate + effective_date)
- Tabla de tipos de cambio históricos (read-only) por moneda

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

---

# Fase 2 — Contactos

### Bloque 2.1 — Backend contactos

```
Implementar bloque 2.1 siguiendo docs/roadmap.md, docs/erd.md y CLAUDE.md.

- app/services/contact_service.py: CRUD + búsqueda (por document_number o business_name con ILIKE/trigram)
- app/api/contacts.py: GET (lista paginada con filtros), GET /{id}, POST, PUT /{id}, DELETE /{id} (soft delete)
- Filtros: ?contact_type=customer|supplier|both, ?search=, ?page=, ?page_size=
- Schemas Pydantic en app/schemas/contacts.py
- Audit log en create/update/delete
```

### Bloque 2.2 — UI lista de contactos

```
Implementar bloque 2.2 siguiendo docs/roadmap.md.

- src/features/contacts/pages/ContactsList.tsx: tabla con paginación server-side, búsqueda, filtro por tipo
- src/features/contacts/api/contacts.ts: funciones de fetch
- src/features/contacts/hooks/useContacts.ts: hook con loading/error/data
- Botón "Nuevo contacto" → navega a /contactos/nuevo
- Click en fila → navega a /contactos/:id

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

### Bloque 2.3 — UI formulario de contacto

```
Implementar bloque 2.3 siguiendo docs/roadmap.md y docs/common-patterns.md (layout de form largo).

- src/features/contacts/pages/ContactForm.tsx: usado para /contactos/nuevo y /contactos/:id
- Campos según docs/erd.md sección 3.1
- Validaciones: business_name requerido, formato de email, document_number requerido si document_type != none
- Botón eliminar con modal de confirmación (solo en modo edición)
- Usar el patrón de layout con flex flex-col h-full + form con overflow-y-auto

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

---

# Fase 3 — Productos

### Bloque 3.1 — Backend categorías

```
Implementar bloque 3.1 siguiendo docs/roadmap.md y docs/erd.md.

- app/services/category_service.py: CRUD + obtener árbol jerárquico
- app/api/categories.py: GET (árbol), GET /{id}, POST, PUT /{id}, DELETE /{id}
- Validación: no permitir ciclos (una categoría no puede ser su propio ancestro)
```

### Bloque 3.2 — Backend productos

```
Implementar bloque 3.2 siguiendo docs/roadmap.md, docs/erd.md y CLAUDE.md.

- Habilitar extensión pg_trgm en una migración Alembic separada
- Crear índice GIN sobre products.name para búsqueda con trigram
- app/services/product_service.py: CRUD + búsqueda optimizada (por SKU exacto, barcode, o nombre con trigram)
- app/api/products.py: CRUD estándar + GET /products/search?q= (devuelve top 20 con score de similitud)
- Schemas Pydantic
- Tests para búsqueda
```

### Bloque 3.3 — Backend unidades de producto

```
Implementar bloque 3.3 siguiendo docs/roadmap.md y docs/erd.md.

REGLAS DE NEGOCIO CRÍTICAS (validar en service, no por constraint):

1. Creación automática de unidad base:
   - Al crear un producto con track_stock=true, crear automáticamente una product_unit con:
     - unit_name = product.base_unit
     - factor_to_base = 1
     - is_default_sale_unit = True
     - is_default_purchase_unit = True
   - Esto garantiza que el producto siempre tiene al menos la unidad base.

2. Unidad base no se puede eliminar nunca (factor_to_base = 1).

3. Una unidad cualquiera no se puede eliminar si tiene movimientos de stock, items de venta, o items de compra asociados.

4. factor_to_base es inmutable después de que la unidad tiene cualquier referencia (stock movement, sale_item, purchase_item, price). Esto evitaría reescribir cantidades históricas.

5. Solo una unidad puede tener is_default_sale_unit=true por producto. Al setear true en una, desmarcar la anterior automáticamente. Mismo para is_default_purchase_unit.

6. La unidad base siempre debe tener al menos una de las dos flags default; si el usuario las saca, dejar un error claro.

- app/services/product_unit_service.py: CRUD anidado bajo productos con las validaciones de arriba
- Endpoints: GET /products/{id}/units, POST /products/{id}/units, PATCH /products/{id}/units/{unit_id}, DELETE
- Tests cubriendo cada una de las 6 reglas
```

### Bloque 3.4 — Backend precios

```
Implementar bloque 3.4 siguiendo docs/roadmap.md, docs/erd.md y docs/design-decisions.md (precios históricos).

DECISIÓN DE DISEÑO: solo se permite agregar precios con effective_from >= último effective_from registrado para esa combinación (product_unit_id, currency_code). No se permite intercalar precios en el pasado. Esto mantiene el modelo simple y consistente.

- app/services/price_service.py:
  - get_current_price(db, product_unit_id, currency_code) -> precio vigente (mayor effective_from <= hoy)
  - add_price(db, product_unit_id, currency_code, price, effective_from, notes, user_id):
    - Validar: effective_from >= último effective_from registrado para esta combinación
    - Si falla: 400 Bad Request "No se pueden cargar precios con fecha anterior al último registrado ({fecha})"
    - Validar: price >= 0
    - Insertar append-only
  - get_price_history(db, product_unit_id, currency_code) -> histórico ordenado por effective_from DESC
- Endpoints:
  - POST /products/{id}/units/{unit_id}/prices
  - GET /products/{id}/units/{unit_id}/prices
- Sin DELETE ni PATCH de precios. La corrección de errores se hace agregando un nuevo precio con la fecha actual.
- Tests: precio vigente correcto con múltiples cambios, rechazo de fechas anteriores, primer precio sin restricción de fecha
```

### Bloque 3.5 — UI lista de productos

```
Implementar bloque 3.5 siguiendo docs/roadmap.md.

CONTEXTO: el endpoint GET /api/v1/stock se crea en Fase 4 (bloque 4.1). En este bloque, NO consumir ese endpoint. La columna de stock se agrega en Fase 4 cuando exista.

- src/features/products/pages/ProductsList.tsx: tabla con búsqueda, filtros por categoría
- Columnas (en este orden):
  1. SKU
  2. Nombre (con barcode debajo en text-xs si existe)
  3. Categoría
  4. Unidad base
  5. Precio vigente en PYG de la default_sale_unit (con tabular-nums)
  6. Estado (activo / inactivo si soft-deleted)
  7. Acciones (editar)
- Búsqueda usa GET /products/search?q= con debounce 300ms
- Filtro de categoría con dropdown (carga el árbol de categorías)
- Toggle "Mostrar inactivos" para ver soft-deleted (default: oculto)
- Botón "Nuevo producto" (.btn-primary) navega a /productos/nuevo
- Click en fila (o icono editar) → /productos/:id
- Paginación server-side (reutilizar patrón de contactos)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), tabular-nums en columna de precio, nunca hex hardcodeados ni text-white directo.
```

### Bloque 3.6 — UI formulario de producto

```
Implementar bloque 3.6 siguiendo docs/roadmap.md y docs/common-patterns.md.

- src/features/products/pages/ProductForm.tsx:
  - Sección principal: SKU, barcode, nombre, descripción, categoría (selector), base_unit, tax_rate, tax_included_in_price, track_stock, low_stock_threshold
  - Sub-sección "Unidades": tabla editable inline (agregar/editar/eliminar unidades con su factor_to_base y flags default)
  - Sub-sección "Precios": tabla con precio vigente por unidad+moneda + botón "Cambiar precio" que abre modal (nuevo registro en product_prices)
- Patrón de scroll anidado para form largo (ver docs/common-patterns.md)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

### Bloque 3.7 — UI categorías

```
Implementar bloque 3.7 siguiendo docs/roadmap.md.

- src/features/admin/pages/Categories.tsx: árbol jerárquico (componente recursivo)
- Cada nodo muestra: nombre + iconos de acción al hover (en mobile siempre visibles):
  - Pencil (editar nombre — inline o modal)
  - Plus (agregar hija)
  - Trash2 (eliminar, con confirmación; no permitir si tiene productos asociados activos)
- Drag-and-drop para reorganizar — opcional, marcar como nice-to-have

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente, nunca hex hardcodeados ni text-white directo.
```

---

# Fase 4 — Compras + Inventario

### Bloque 4.1 — Backend stock_movements + stock_current

```
Implementar bloque 4.1 siguiendo docs/roadmap.md, docs/erd.md, CLAUDE.md y
docs/common-patterns.md (sección lock pesimista).

ESTE BLOQUE ES EL CORAZÓN DEL SISTEMA DE STOCK. Plan mode obligatorio.
Tests primero donde sea posible (TDD).

MODELOS (verificar contra erd.md):
- StockMovement: ya existe en schema inicial. Verificar que el modelo SQLAlchemy
  esté completo y los relationships funcionen.
- StockCurrent: ya existe en schema inicial. Verificar PK compuesta (product_id, warehouse_id).

SERVICE app/services/stock_service.py:

- apply_movement(db, *, product_id, warehouse_id, movement_type, direction,
  quantity_base, unit_cost_base=None, reference_type=None, reference_id=None,
  user_id, notes=None) → StockMovement

  Implementar EXACTAMENTE el patrón de docs/common-patterns.md sección
  "Lock pesimista para actualización de stock". Atención especial a:
  - SELECT ... FOR UPDATE sobre stock_current antes de cualquier modificación
  - Si stock_current no existe para el producto+depósito, crearlo con qty=0, avg_cost=0
  - Validación de stock negativo según setting allow_negative_stock (consultar
    settings_service)
  - Cálculo de CPP para direction=IN: nuevo_avg = (qty_actual * avg_actual +
    qty_nueva * costo_nuevo) / (qty_actual + qty_nueva). Si stock_actual +
    qty_nueva = 0 (caso edge), mantener avg_actual.
  - Para direction=OUT, avg_cost_base NO se modifica
  - Inserta StockMovement primero, después actualiza StockCurrent. Todo en la
    transacción exterior — esta función NO hace commit.
  - Excepciones custom: InsufficientStockError(product_id, available, requested),
    InvalidStockMovementError (datos inconsistentes)

- get_current_stock(db, product_id, warehouse_id=None) → StockCurrent | list[StockCurrent]
  Si warehouse_id es None, devuelve stock en todos los depósitos para ese producto.

- get_stock_summary(db, *, warehouse_id=None, search=None, low_stock_only=False,
  page=1, page_size=50) → paginado
  Lista productos con su stock actual. JOIN con products + units_catalog para
  hidratar nombres. Filtros y paginación al estilo list_products.

- get_movements(db, *, product_id=None, warehouse_id=None, reference_type=None,
  reference_id=None, date_from=None, date_to=None, page=1, page_size=50) → paginado
  Historial filtrable. Usado por kardex (Fase 6) y por vista detalle de compra/venta.

- apply_initial_inventory(db, *, items: list[InitialInventoryItem],
  warehouse_id, user_id) → list[StockMovement]

  Cada item: product_id, quantity_base, unit_cost_base.
  Validación CRÍTICA: para cada producto, verificar que NO existan movements
  previos en ese depósito. Si los hay → InitialInventoryAlreadyAppliedError
  con el product_id.
  Ordenar items por product_id antes de aplicar (prevenir deadlocks).
  Genera movements con movement_type='initial', direction='in'.

- recalculate_stock_current(db, *, warehouse_id=None, product_id=None) → dict
  Reconstruye stock_current desde el ledger. Útil para detectar inconsistencias
  o recuperar tras corrupción. Itera movements cronológicamente, recalcula CPP,
  upsertea stock_current. Devuelve dict {product_id: {qty, avg_cost}} con los
  resultados.

API app/api/stock.py:

- GET /api/v1/stock?warehouse_id=&search=&low_stock_only=&page=&page_size=
  → lista paginada de stock actual
- GET /api/v1/stock/products/{product_id} → stock del producto en todos los depósitos
- GET /api/v1/stock/movements?product_id=&warehouse_id=&date_from=&date_to=&page=&page_size=
  → historial paginado
- POST /api/v1/stock/initial → recibe lista de items + warehouse_id, aplica
  inventario inicial. Body: { warehouse_id, items: [{product_id, quantity_base,
  unit_cost_base}] }

SCRIPT app/scripts/recalculate_stock.py:
- Standalone: python -m app.scripts.recalculate_stock --warehouse <id>
- Llama a stock_service.recalculate_stock_current
- Muestra resumen de cambios aplicados

PATRÓN OBLIGATORIO PARA EVITAR DEADLOCKS:
Cuando una operación aplique múltiples movements en una transacción (confirm
de compra/venta, inventario inicial), los items DEBEN procesarse ordenados
por product_id (o tupla product_id + warehouse_id). Esto garantiza que todas
las transacciones tomen locks en el mismo orden y previene deadlocks de PostgreSQL.

TESTS CRÍTICOS (en app/tests/test_stock_service.py):
- CPP correcto en compras múltiples del mismo producto con costos distintos
- CPP correcto con cantidad fraccional (NUMERIC, no float)
- Stock negativo bloqueado cuando allow_negative_stock=false
- Stock negativo permitido cuando allow_negative_stock=true
- Inventario inicial rechaza productos con movements previos
- Inventario inicial ordena por product_id internamente (verificar con mock)
- Lock pesimista: test con asyncio.gather() de dos apply_movement concurrentes
  sobre el mismo producto, verificar que las cantidades finales son consistentes
- recalculate_stock_current produce mismos valores que la suma incremental

Plan mode obligatorio. Test-first donde sea posible.
```

### Bloque 4.2 — Backend compras

```
Implementar bloque 4.2 siguiendo docs/roadmap.md, docs/erd.md y CLAUDE.md.

Plan mode obligatorio.

MODELOS:
- Purchase y PurchaseItem ya existen en schema inicial. Verificar que estén
  completos según erd.md y que los relationships estén bien.

SERVICE app/services/purchase_service.py:

- create_purchase(db, *, data, user_id) → Purchase
  Crea cabecera con status='draft'. supplier_id debe ser contacto válido
  (type=supplier o both, no borrado). Currency válida y activa. exchange_rate
  obligatorio (si moneda != base, validar consistencia con exchange_rates vigente).
  warehouse_id debe existir. Audit log con action='create'.

- update_purchase(db, *, purchase_id, data, user_id) → Purchase
  Solo permite cambios si status='draft'. Si confirmed/cancelled →
  InvalidPurchaseStateError. Audit log con action='update'.

- add_item(db, *, purchase_id, data, user_id) → PurchaseItem
  Solo si status='draft'. Validaciones:
    - product_id existe y no borrado
    - product_unit_id existe, pertenece al producto, no inactivo
    - quantity > 0
    - unit_cost >= 0
  Calcula snapshots:
    - quantity_base = quantity * product_unit.factor_to_base
    - unit_cost_base_currency = unit_cost * purchase.exchange_rate
    - tax_rate = producto.tax_rate (snapshot)
    - tax_included = producto.tax_included_in_price (snapshot)
    - subtotal, tax_amount, total según las fórmulas estándar
  Recalcula totales de la cabecera (subtotal, tax_total, total, total_base_currency).
  Audit log con action='update' sobre la cabecera.

- update_item(db, *, purchase_id, item_id, data, user_id) → PurchaseItem
  Solo en draft. Recalcula snapshots y totales de cabecera.

- remove_item(db, *, purchase_id, item_id, user_id) → None
  Solo en draft. Hard delete (no soft, items son inseparables del header).
  Recalcula totales de cabecera.

- confirm_purchase(db, *, purchase_id, user_id) → Purchase
  TRANSACCIÓN ATÓMICA. Plan mode estricto.
    1. Validar status='draft' y que tiene al menos 1 item
    2. Cambiar status='confirmed', setear confirmed_at, updated_by_user_id
    3. Ordenar items por product_id (prevenir deadlocks — patrón obligatorio del 4.1)
    4. Para cada item: stock_service.apply_movement(direction='in',
       movement_type='purchase', reference_type='purchase', reference_id=purchase.id,
       quantity_base=item.quantity_base, unit_cost_base=item.unit_cost_base_currency)
    5. Audit log con action='confirm' sobre la cabecera
  Si cualquier paso falla, rollback completo.

- cancel_purchase(db, *, purchase_id, user_id, reason: str) → Purchase
  Solo si status='confirmed'. Recibe reason obligatorio.
    1. Cambiar status='cancelled', cancelled_at, cancelled_reason
    2. Ordenar items por product_id
    3. Para cada item: stock_service.apply_movement(direction='out',
       movement_type='return_out', reference_type='purchase', reference_id=purchase.id,
       quantity_base=item.quantity_base, unit_cost_base=item.unit_cost_base_currency)
    4. Audit log con action='cancel'
  CPP no se recalcula hacia atrás (decisión documentada en design-decisions.md).
  Si cualquier paso falla, rollback completo.

- list_purchases(db, *, supplier_id=None, status=None, date_from=None,
  date_to=None, warehouse_id=None, page=1, page_size=20) → paginado
  JOIN con contacts para hidratar nombre del proveedor.

- get_purchase(db, purchase_id) → Purchase con items + supplier hidratados
  Eager load con selectinload.

- generate_purchase_number(db) → str
  Formato YYYY-NNNNNN. Atómico contra race conditions: usar SELECT FOR UPDATE
  sobre una tabla counters o similar, O usar SELECT MAX(...) con retry en
  IntegrityError. Documentar la decisión en docs/design-decisions.md.

API app/api/purchases.py:
- GET /api/v1/purchases (lista paginada con filtros)
- GET /api/v1/purchases/{id} (con items + supplier)
- POST /api/v1/purchases (crea draft, 201)
- PATCH /api/v1/purchases/{id} (actualiza cabecera en draft)
- POST /api/v1/purchases/{id}/items (agrega item, 201)
- PATCH /api/v1/purchases/{id}/items/{item_id}
- DELETE /api/v1/purchases/{id}/items/{item_id} (204)
- POST /api/v1/purchases/{id}/confirm (200, devuelve compra actualizada)
- POST /api/v1/purchases/{id}/cancel (200, body con reason)
- DELETE /api/v1/purchases/{id} (204, solo drafts, hard delete)

TESTS:
- confirm aplica movements correctos, actualiza CPP correctamente
- confirm de compra USD aplica unit_cost_base_currency con conversion
- cancel genera movements compensatorios sin recalcular CPP
- No se puede confirmar dos veces
- No se puede agregar items a compra confirmed
- update_purchase rechaza cambios en confirmed
- Deadlock prevention: items se ordenan por product_id antes de apply
- generate_purchase_number es único bajo concurrencia (test con asyncio.gather)
- Audit log se registra en create, update, confirm, cancel

Plan mode obligatorio.
```

### Bloque 4.3 — UI lista de compras

```
Implementar bloque 4.3 siguiendo docs/roadmap.md.

- src/features/purchases/pages/PurchasesList.tsx: tabla con filtros (proveedor, fecha, estado)
- Badge de estado con color (gris=draft, verde=confirmed, rojo=cancelled)
- Click en fila → si status=draft navega a `/compras/:id` en modo edición; si confirmed/cancelled navega a `/compras/:id` en modo lectura
- Botón "Nueva compra"

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo. Estados: draft = text-text-secondary, confirmed = success-500, cancelled = danger-500.
```

### Bloque 4.4 — UI formulario de compra

```
Implementar bloque 4.4 siguiendo docs/roadmap.md.

- src/features/purchases/pages/PurchaseForm.tsx:
  - Cabecera: selector de proveedor (autocomplete sobre contacts type=supplier|both), fecha, supplier_document_number, moneda, exchange_rate (sugerido pero editable), depósito, notas
  - Tabla de items: buscar producto (autocomplete), seleccionar product_unit, cantidad, costo unitario (en moneda de la compra), IVA (default del producto), botón eliminar fila
  - Resumen: subtotal, IVA, total (en moneda de la compra y en PYG)
  - Botones: "Guardar como borrador", "Confirmar compra" (con modal de confirmación mostrando impacto en stock)
- Modo edición: solo se puede editar si status=draft. Si confirmed, vista de solo lectura con botón "Cancelar compra"

FLUJO DE CREACIÓN (consistente con productos y contactos):
- /compras/nueva: formulario en memoria, sin draft creado todavía
- Al hacer "Guardar como borrador" por primera vez: POST a /api/v1/purchases →
  redirige a /compras/:id con el draft creado
- A partir de ahí, cada cambio es PATCH/POST/DELETE inmediato sobre el draft
- "Confirmar compra" solo disponible cuando hay al menos 1 item y todos los
  campos requeridos están llenos

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo. Columnas numéricas con tabular-nums.
```

### Bloque 4.5 — UI vista detalle de compra

```
Implementar bloque 4.5 siguiendo docs/roadmap.md.

- Reusar PurchaseForm en modo lectura si status != draft
- Modal "Cancelar compra" con campo de motivo obligatorio
- Mostrar audit log de la compra (creación, confirmación, cancelación con usuario y fecha)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .btn-danger para cancelar, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

### Bloque 4.6 — UI inventario inicial

```
Implementar bloque 4.6 siguiendo docs/roadmap.md.

- src/features/admin/pages/InitialInventory.tsx: tabla con todos los productos con track_stock=true
- Por cada producto: input de cantidad inicial (en base_unit) + costo unitario inicial
- Botón "Cargar inventario inicial" → para cada fila con cantidad > 0, llama al endpoint POST /api/v1/stock/initial (ya creado en bloque 4.1)
- Validación frontend: avisar al usuario si algún producto ya tiene movimientos previos (el backend devuelve 409 con la lista)
- Solo accesible para rol admin

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo. Columnas numéricas con tabular-nums.
```

---

# Fase 5 — Ventas (POS)

### Bloque 5.1 — Backend ventas

```
Implementar bloque 5.1 siguiendo docs/roadmap.md, docs/erd.md y CLAUDE.md.

- app/services/sale_service.py:
  - create_sale(db, data, user_id) — crea cabecera (puede ir directo a confirmed desde POS)
  - confirm_sale(db, sale_id, user_id) — transacción atómica:
    1. Validar customer_id si settings.sale_requires_customer
    2. Para cada item: apply_movement (out) con snapshot de unit_cost_base_at_sale = stock_current.avg_cost_base actual
    3. Validar suma de payments = total
    4. Calcular total_base_currency y cost_total_base
  - cancel_sale(db, sale_id, user_id, reason) — movements compensatorios (return_in)
  - generate_sale_number() — correlativo
- app/api/sales.py: CRUD + confirm + cancel
- Tests críticos: stock se descuenta correctamente, validación de stock negativo, snapshot de costo correcto, pagos mixtos validados

Plan mode obligatorio.
```

### Bloque 5.2 — UI POS — layout principal

```
Implementar bloque 5.2 siguiendo docs/roadmap.md y CLAUDE.md (sección POS).

- src/features/pos/pages/POS.tsx:
  - Sin AppLayout normal — pantalla completa con su propio header minimal
  - Grid de 2 columnas: izquierda (búsqueda + carrito) ~70%, derecha (resumen + cliente + cobro) ~30%
  - Tab order respetando CLAUDE.md
  - Indicador visual claro del campo activo (ring de Tailwind)
- Ruta /pos accesible desde sidebar y con shortcut global (a definir)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo. El POS usa tabular-nums en todos los totales y precios.
```

### Bloque 5.3 — UI POS — búsqueda y carrito

```
Implementar bloque 5.3 siguiendo docs/roadmap.md.

- Campo de búsqueda con debounce 200ms, consume GET /api/v1/products/search?q=
- Resultados como dropdown navegable con ↑/↓ y Enter
- Al seleccionar producto: muestra unidades disponibles, default es is_default_sale_unit
- Campos: cantidad (default 1), unidad (selector)
- Enter agrega al carrito y vuelve foco a búsqueda con campo limpio
- Carrito: lista con producto, unidad, cantidad (editable inline con flechas o input), precio unitario, subtotal, botón eliminar
- Cálculo en vivo de totales

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.input, .label, .card), nunca hex hardcodeados ni text-white directo. Todos los precios y totales con tabular-nums.
```

### Bloque 5.4 — UI POS — cliente y descuentos

```
Implementar bloque 5.4 siguiendo docs/roadmap.md.

- F2 abre modal de selección de cliente (autocomplete sobre contacts type=customer|both)
- Cliente seleccionado se muestra en el resumen lateral con botón "x" para quitar
- F3 abre modal de descuento:
  - Si hay item seleccionado en carrito: descuento de item
  - Si no: descuento de cabecera
  - Opciones: monto o porcentaje
  - Aplicar guarda en sale_items.discount_amount/percent o sales.header_discount_*
- Mostrar descuentos aplicados en el carrito y en el resumen

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

### Bloque 5.5 — UI POS — cobro y confirmación

```
Implementar bloque 5.5 siguiendo docs/roadmap.md.

- F4 abre modal de cobro:
  - Lista de pagos (inicialmente vacía o con un pago default = total en efectivo)
  - Agregar pago: método (select), monto, referencia (opcional)
  - Validación en vivo: suma de pagos vs total
  - Mostrar diferencia (a cobrar o vuelto)
  - Botón "Cobrar" habilitado solo si suma == total
- Al cobrar: llama POST /api/v1/sales con todo el carrito + payments, status=confirmed
- Si éxito: mostrar confirmación visual (toast grande o pantalla intermedia con ticket resumido), limpiar carrito, foco vuelve a búsqueda
- Si error de stock: mostrar mensaje claro indicando qué producto y cuánto falta
- F9 cancela venta en progreso (limpia carrito tras confirmación)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.input, .label, .card), nunca hex hardcodeados ni text-white directo. **El botón "Cobrar" usa .btn-accent — es el único lugar del sistema donde se usa cyan, ver docs/design-system.md regla 4.** Total y vuelto con tabular-nums en tamaño grande (text-3xl font-bold).
```

### Bloque 5.6 — UI lista de ventas

```
Implementar bloque 5.6 siguiendo docs/roadmap.md.

- src/features/sales/pages/SalesList.tsx: tabla con filtros (fecha, cliente, estado, vendedor)
- Vista detalle (modal o página) con todos los items y pagos
- Botón "Cancelar venta" en ventas confirmadas (con motivo, modal de confirmación)

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .btn-danger para cancelar, .input, .label, .card), nunca hex hardcodeados ni text-white directo. Columnas de montos con tabular-nums.
```

### Bloque 5.7 — Shortcuts y accesibilidad

```
Implementar bloque 5.7 siguiendo docs/roadmap.md y CLAUDE.md (sección POS).

- F1 abre modal con todos los shortcuts del POS
- Hook useKeyboardShortcuts que centraliza los listeners
- Sonido al confirmar venta (opcional, controlable por setting pos_play_sound_on_sale)
- Indicador visual del campo activo (ya implementado en 5.2, revisar consistencia)
- Tests manuales: recorrer una venta entera sin tocar el mouse

Aplicar docs/design-system.md: el modal de ayuda usa bg-bg-elevated con tabla limpia mostrando shortcut + descripción. Nunca hex hardcodeados ni text-white directo.
```

---

# Fase 6 — Ajustes + Reportes

### Bloque 6.1 — Backend ajustes

```
Implementar bloque 6.1 siguiendo docs/roadmap.md y docs/erd.md.

- app/services/adjustment_service.py: CRUD + confirm + cancel (similar a compras)
- Confirmación: genera movements (in u out según direction de cada item) y actualiza stock_current
- Cancelación: movements compensatorios
- app/api/adjustments.py
```

### Bloque 6.2 — UI ajustes

```
Implementar bloque 6.2 siguiendo docs/roadmap.md.

- src/features/adjustments/pages/AdjustmentsList.tsx
- src/features/adjustments/pages/AdjustmentForm.tsx:
  - Cabecera: depósito, fecha, motivo (select)
  - Items: producto, unidad, cantidad (puede ser positiva o negativa), costo si es ingreso
  - Estados draft/confirmed/cancelled

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo. Columnas numéricas con tabular-nums.
```

### Bloque 6.3 — Backend reportes

```
Implementar bloque 6.3 siguiendo docs/roadmap.md.

- app/services/report_service.py:
  - sales_by_period(db, date_from, date_to, group_by='day'|'week'|'month')
  - top_products(db, date_from, date_to, limit=10)
  - profit_by_product(db, date_from, date_to) — usa unit_cost_base_at_sale
  - low_stock_products(db, warehouse_id=None)
  - stock_value(db, warehouse_id=None) — sum(quantity_base * avg_cost_base)
  - movements_by_product(db, product_id, warehouse_id, date_from, date_to) — kardex
- app/api/reports.py
- Queries optimizadas con índices apropiados
- Todos los montos devueltos en PYG (moneda base)
```

### Bloque 6.4 — UI dashboard (Home)

```
Implementar bloque 6.4 siguiendo docs/roadmap.md.

- src/features/dashboard/pages/Home.tsx:
  - Métricas del mes (4 cards): ventas totales, cantidad de ventas, ticket promedio, utilidad
  - Recharts BarChart: ventas por día del mes
  - Recharts PieChart: top 10 productos vendidos del mes
  - Lista de productos con stock bajo (con link)
  - Card con valor total del inventario
- Componente reutilizable MetricCard
- Hook useDashboard que consume varios endpoints en paralelo

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clase .card para las métricas, nunca hex hardcodeados ni text-white directo. Todos los montos con tabular-nums. Recharts: configurar colores con los tokens primary-500, success-500, warning-500, danger-500 (no usar paleta default de Recharts). Stock bajo mostrado con warning-500, no danger.
```

### Bloque 6.5 — UI página de reportes

```
Implementar bloque 6.5 siguiendo docs/roadmap.md.

- src/features/reports/pages/Reports.tsx con tabs o subnavegación:
  - "Ventas por período" (gráfico + tabla)
  - "Top productos" (tabla)
  - "Utilidad por producto" (tabla)
  - "Kardex" (selector de producto + tabla de movements)
  - "Valor de inventario" (tabla)
- Cada reporte: selector de fechas + botón "Exportar CSV"
- Decisión a tomar durante implementación: exportación CSV implementada o se difiere

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo. Todas las columnas numéricas con tabular-nums. Recharts con colores del sistema.
```

---

# Fase 7 — Pulido y entrega

### Bloque 7.1 — Tests del backend

```
Implementar bloque 7.1 siguiendo docs/roadmap.md y CLAUDE.md.

CONFIGURACIÓN DE TESTS:
- pytest con pytest-asyncio y httpx para tests de API
- BD de tests separada: usar DATABASE_URL_TEST en .env.test
- Fixture session-scoped que crea la BD de tests al inicio y la borra al final
- Fixture function-scoped con transacción + rollback por test
- pytest.ini con asyncio_mode = auto

SERVICES A CUBRIR (orden de prioridad):
1. stock_service: apply_movement (CPP correcto con compras múltiples, lock
   pesimista con asyncio.gather, stock negativo según setting, casos edge
   qty+nueva=0); apply_initial_inventory (rechaza productos con movements
   previos, ordena por product_id); recalculate_stock_current (consistencia
   ledger vs cache)
2. purchase_service: confirm (movements correctos, CPP actualizado, audit log),
   cancel (compensación sin recalcular CPP), no se puede confirmar dos veces,
   compra en USD aplica conversión correcta
3. sale_service: confirm (lock, snapshot de costo, validación de stock,
   suma de payments=total, requires_customer setting), cancel (compensación),
   pagos mixtos
4. adjustment_service: confirm (movements según direction), cancel (compensación),
   manejo de cancel cuando original era OUT sin costo
5. price_service: precio vigente con múltiples cambios, rechazo de fechas
   anteriores al último
6. report_service: cada función con datos seed que cubra ventas multimoneda,
   cancelaciones, casos vacíos, y los bugs encontrados durante QA cruzado
   (si los hay)
7. settings_service: parseo de cada value_type, cache invalidation

REGRESIONES BASADAS EN QA REAL:
Agregar al menos un test por cada bug encontrado durante QA de Fase 6
(QA cruzado contra BD). Documentar en docstring del test "Reproduce bug
encontrado en QA de Fase 6: ..." para trazabilidad.

COVERAGE:
- Objetivo: ≥80% en services
- Ignorar: routers (cobertura indirecta vía tests de integración cuando
  se hagan), schemas (son declarativos), modelos
- Generar reporte con pytest --cov=app.services --cov-report=html

DOCUMENTAR EN docs/comandos.md:
- Cómo correr tests localmente
- Cómo crear la BD de tests
- Cómo interpretar el coverage report
```

### Bloque 7.2 — Manejo de errores y validaciones finales

```
Revisar y endurecer manejo de errores en todo el sistema.

Backend:
- Auditar todos los endpoints: códigos HTTP correctos (400 vs 404 vs 409 vs 422)
- Mensajes de error claros (no leak de internals)
- Logs estructurados con loguru o logging configurado en app/logging.py
- Excepciones custom en app/exceptions.py (InsufficientStockError, etc.)

Frontend:
- Manejo de errores de red en hooks de fetch
- Toast de error consistente
- Mensajes traducidos al español
```

### Bloque 7.3 — Sidebar colapsable

```
Implementar bloque 7.3 siguiendo docs/roadmap.md.

- Modificar src/components/AppLayout.tsx y Sidebar.tsx para soportar tres estados: expanded, collapsed, hidden
- Botón en header (icono PanelLeft de Lucide) para ciclar entre los tres estados
- Store Zustand en src/lib/uiStore.ts (o similar) con el estado actual del sidebar
- Persistencia en localStorage con key 'dtcore_sidebar_state'
- Estados visuales:
  - expanded: ~200px, iconos + texto (estado default)
  - collapsed: ~60px, solo iconos, tooltip al hover con el nombre del módulo
  - hidden: 0px, sidebar fuera de pantalla
- Transición suave: transition-all duration-200
- En POS (/pos) el sidebar ya está oculto por diseño (bloque 5.2) — verificar que el toggle no aplica ahí

Aplicar docs/design-system.md: tooltip usa bg-bg-elevated, transición suave consistente con el resto del sistema.
```

### Bloque 7.4 — Responsive básico para vista mobile

```
Implementar bloque 7.4 siguiendo docs/roadmap.md.

OBJETIVO: el cliente puede consultar reportes desde el celular cuando está fuera del local. NO optimizar para operar el sistema desde móvil (eso es v2).

CAMBIOS PRINCIPALES:

1. Breakpoint principal: md (768px). En < md aplicar:
   - Sidebar se convierte en drawer (menú hamburguesa) que se abre desde la izquierda con overlay
   - Header muestra botón hamburguesa (icono Menu de Lucide) en lugar de botón de toggle
   - Click fuera del drawer lo cierra

2. Páginas a optimizar para mobile:
   - Home (Dashboard): cards apiladas verticalmente (grid-cols-1 en < md), gráficos full-width
   - Reportes: tabs scrollables horizontalmente si no entran, filtros colapsables en accordion
   - Ventas (lista): tabla con scroll horizontal, columnas críticas visibles primero (fecha, cliente, total)
   - Compras (lista): igual que ventas
   - Login: ya debería verse bien, verificar

3. Páginas que NO se rediseñan para mobile en v1 (se ven en zoom de escritorio, documentar limitación):
   - POS
   - Formularios de compra/venta
   - Formularios de productos
   - Ajustes de stock
   - Panel admin de settings

4. Actualizar README del cliente con la sección "Uso desde celular":
   - Recomendado: solo consulta de reportes y dashboard
   - Para operación: usar PC o notebook

5. Tests manuales:
   - Verificar en Chrome DevTools (modo mobile, iPhone 12 / Pixel 5)
   - Verificar en celular real del desarrollador conectado a la red local

Aplicar docs/design-system.md: el drawer usa bg-bg-surface con sombra, overlay con bg-bg-base/80 (80% opacidad). Nunca hex hardcodeados ni text-white directo.
```

### Bloque 7.5 — Documentación de deployment

```
Crear docs/deployment.md con dos secciones:

SECCIÓN A — Deployment con Docker (para entornos con virtualización):
- Requisitos previos (Docker Desktop instalado, Node, Python para venv)
- Clonado del repo
- Configurar .env (DATABASE_URL, JWT_SECRET, STORAGE_PATH, etc.)
- docker compose up -d
- Migración + seed
- Build del frontend + servirlo (sugerir `serve -s dist -l 4173`)
- Configuración de rclone para backups
- Cron / Task Scheduler para backups diarios
- Configuración de IP fija en el router del cliente
- Importación de certificado mkcert en dispositivos del cliente
- Smoke test detallado (ver abajo)

SMOKE TEST POST-INSTALACIÓN (lista accionable, 15 verificaciones):
1. Login con admin/password — entra al dashboard
2. Crear un producto de prueba — guarda y aparece en lista
3. Cargar inventario inicial de ese producto — stock se refleja
4. Crear un proveedor — guarda
5. Crear una compra del producto — guardar como borrador
6. Confirmar la compra — stock aumenta, CPP correcto
7. Crear un cliente — guarda
8. Abrir POS, vender 1 unidad — confirma, stock baja
9. Ver dashboard — métricas reflejan la venta
10. Abrir reportes — top productos muestra el producto
11. Ejecutar backup manual — archivo se sube a Drive
12. Reiniciar la PC — todos los servicios arrancan automáticamente
13. Acceder desde celular en la misma WiFi — login funciona en https
14. Hacer F5 en una ruta protegida — no redirige a inicio
15. Cancelar la venta de prueba — stock vuelve, dashboard se actualiza

PLAN DE ROLLBACK:
- Cómo restaurar desde backup en caso de problemas
- Comandos exactos de pg_restore
- Qué hacer si una migración falla a mitad

PROCEDIMIENTO DE ACTUALIZACIONES:
- git pull
- pip install -r requirements.txt (si cambió)
- npm install (si cambió) + rebuild del frontend
- alembic upgrade head
- Reiniciar servicios
- Smoke test reducido (5-7 puntos)
```

### Bloque 7.5b - Setup sin Docker para Windows

---

Crear docs/deployment.md SECCIÓN B — Deployment nativo en Windows (sin Docker).

CONTEXTO: para clientes sin virtualización habilitada o con PCs de bajos
recursos donde Docker es overhead injustificado.

REQUISITOS PREVIOS:

- Windows 10/11 con permisos de admin
- Python 3.12+ (instalador oficial, marcar "Add to PATH")
- Node.js 20+ LTS (instalador oficial)
- PostgreSQL 16 (instalador EDB) — durante instalación, anotar la password
  del superuser postgres
- Git para Windows

INSTALACIÓN POSTGRESQL:

- Instalar PostgreSQL 16 con valores default (puerto 5432, locale es_PY)
- Crear usuario y BD con pgAdmin o psql:
  CREATE USER dtcore_admin WITH PASSWORD '<password seguro>';
  CREATE DATABASE dtcore_db OWNER dtcore_admin;
- Verificar conexión: psql -U dtcore_admin -d dtcore_db -h localhost

INSTALACIÓN BACKEND:

- Clonar el repo en C:\dtcore (o ruta elegida)
- cd backend
- python -m venv .venv
- .venv\Scripts\activate
- pip install -r requirements.txt
- Crear .env con DATABASE_URL=postgresql+asyncpg://dtcore_admin:...@localhost:5432/dtcore_db
  y demás variables
- alembic upgrade head
- python -m app.seed.run
- Probar: uvicorn app.main:app --host 0.0.0.0 --port 8000

INSTALACIÓN FRONTEND:

- cd frontend
- npm install
- Configurar .env del frontend con VITE_API_URL=https://<ip-lan-del-server>/api
- npm run build
- Probar: npx serve -s dist -l 4173 --ssl-cert ... (con cert mkcert)

ARRANQUE AUTOMÁTICO:
Configurar como servicios de Windows. Opción recomendada: NSSM (Non-Sucking
Service Manager, gratis y simple). Crear servicios para:

1. dtcore-backend:
   - Path: C:\dtcore\backend\.venv\Scripts\uvicorn.exe
   - Args: app.main:app --host 0.0.0.0 --port 8000
   - Startup: Automatic
   - Log on: Local System

2. dtcore-frontend:
   - Path: C:\Program Files\nodejs\npx.cmd
   - Args: serve -s C:\dtcore\frontend\dist -l 4173 --ssl-cert ...
   - Startup: Automatic

PostgreSQL ya se registra como servicio automático al instalarse.

CONFIGURACIÓN DE BACKUPS:

- Crear C:\dtcore\scripts\backup.ps1 (script PowerShell):
  - Llama a pg_dump.exe con flags apropiados
  - Comprime el dump (.zip o .sql.gz si tenés gzip)
  - Llama a rclone.exe con la ruta de Drive configurada
  - Logea resultado en C:\dtcore\logs\backup.log
- Configurar tarea programada (Task Scheduler) que corra el .ps1 diariamente
  a las 2 AM
- Política de retención: borrar dumps locales >30 días en el mismo script

CONFIGURACIÓN DE rclone (paso a paso):

- Descargar rclone.exe a C:\dtcore\tools\
- rclone config (interactivo) — configurar remote Google Drive
- Hacer un rclone copy de prueba

LOGS:

- Backend uvicorn → C:\dtcore\logs\backend.log (configurar uvicorn con
  --log-config logging.json)
- PostgreSQL → ruta default del instalador
- Backups → C:\dtcore\logs\backup.log

CONFIGURACIÓN DE FIREWALL DE WINDOWS:

- Permitir puertos 8000 (backend) y 4173 (frontend) en perfil de red privada

CONFIGURACIÓN DE IP FIJA EN ROUTER DEL CLIENTE:
(igual que sección A)

IMPORTACIÓN DE CERTIFICADO MKCERT EN DISPOSITIVOS:
(igual que sección A)

SMOKE TEST POST-INSTALACIÓN:
(mismas 15 verificaciones que sección A)

PLAN DE ROLLBACK:

- pg_restore desde backup
- Comandos específicos para Windows

PROCEDIMIENTO DE ACTUALIZACIONES:

- git pull
- cd backend && .venv\Scripts\activate && pip install -r requirements.txt &&
  alembic upgrade head
- cd frontend && npm install && npm run build
- Reiniciar servicios: nssm restart dtcore-backend && nssm restart dtcore-frontend
- Smoke test reducido

---

### Bloque 7.6 — Datos iniciales del cliente

```
Coordinar con el cliente carga inicial.

CREAR EN scripts/:
- products_template.csv: SKU, nombre, descripción, categoría, unidad_base,
  tax_rate, tax_included_in_price, low_stock_threshold (con header en español
  y 3-5 filas de ejemplo)
- contacts_template.csv: tipo (cliente/proveedor/ambos), documento_tipo,
  documento_numero, razon_social, nombre_fantasia, telefono, email, direccion
- initial_inventory_template.csv: SKU, cantidad, costo_unitario_pyg

CREAR scripts/import_initial_data.py:
- Comando: python -m app.scripts.import_initial_data --file <ruta>.csv --type <products|contacts|inventory>
- Validación PRIMERO, importación SEGUNDO:
  - Para productos: SKUs duplicados, categorías existentes, unidades del
    catálogo, tax_rate válido (0/5/10)
  - Para contactos: tipos válidos, formatos de documento, emails parseables
  - Para inventario: SKUs existentes, no debe tener movements previos,
    cantidades > 0
- Si hay errores: NO importa NADA, devuelve reporte con línea + error
- Si valida: importa todo en transacción
- Modo dry-run con --dry-run para validar sin escribir

ORDEN DE CARGA RECOMENDADO (documentar en deployment.md):
1. Verificar units_catalog (seed automático)
2. Crear/verificar categorías (manual o con import)
3. Importar productos
4. Importar contactos
5. Importar inventario inicial

PROCESO CON EL CLIENTE:
- Enviarle los 3 templates por email/whatsapp
- Pedirle que llene en Excel/Google Sheets, exporte a CSV UTF-8
- Validar con --dry-run antes de importar
- Importar
- Verificar con smoke test
```

### Bloque 7.7 — Capacitación

```
No es un bloque de código. Preparar materiales:
- Guía corta impresa con shortcuts del POS
- Video corto (opcional) de operaciones básicas
- Sesión presencial: instalación de PWA, importación de certificado, primer login, primera venta de prueba
```

### Bloque 7.8 — Período de acompañamiento

```
No es un bloque de código. Mantener:
- Backlog de feedback del cliente en GitHub Issues o similar
- Cada bug crítico → fix inmediato con su test
- Cada feature request → evaluar si es v1 (incluido) o v2 (cotizable aparte)
- Revisión semanal de logs y backups durante el primer mes
```

---

## Nota sobre flexibilidad

Los prompts son guías, no contratos. Si durante un bloque Claude Code (o el desarrollador) detecta:

- Una decisión arquitectónica no resuelta → parar, volver a Claude.ai
- Un bloque más grande de lo esperado → partir en sub-bloques sobre la marcha
- Una dependencia faltante con otro bloque → resolver antes de continuar

Cuando esto pase, actualizar `HANDOFF.md` con la decisión tomada antes de seguir.
