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

- app/services/product_unit_service.py: CRUD anidado bajo productos
- Validaciones (en service, no por constraint):
  - Al crear/actualizar: si is_default_sale_unit=true, desmarcar el anterior default
  - Mismo para is_default_purchase_unit
  - Al borrar: no permitir si es la única unidad o si está referenciada en ventas/compras
- Endpoints: GET /products/{id}/units, POST /products/{id}/units, PUT /products/{id}/units/{unit_id}, DELETE
```

### Bloque 3.4 — Backend precios

```
Implementar bloque 3.4 siguiendo docs/roadmap.md, docs/erd.md y docs/design-decisions.md (precios históricos).

- app/services/price_service.py:
  - get_current_price(db, product_unit_id, currency_code) -> precio vigente
  - add_price(db, product_unit_id, currency_code, price, effective_from, user_id) -> nuevo registro append-only
  - get_price_history(db, product_unit_id, currency_code) -> histórico ordenado
- Endpoints: POST /products/{id}/units/{unit_id}/prices, GET /products/{id}/units/{unit_id}/prices
```

### Bloque 3.5 — UI lista de productos

```
Implementar bloque 3.5 siguiendo docs/roadmap.md.

- src/features/products/pages/ProductsList.tsx: tabla con búsqueda, filtros por categoría
- Mostrar stock actual del depósito default (consumir GET /api/v1/stock?warehouse_id=default)
- Indicador visual rojo cuando stock <= low_stock_threshold (del producto o del setting default)
- Botón "Nuevo producto"

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
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
- CRUD inline: doble-click para editar nombre, botón "+" para agregar hija, botón "x" para eliminar (con confirmación)
- Drag-and-drop para reorganizar — opcional, marcar como nice-to-have

Aplicar docs/design-system.md: usar tokens semánticos (bg-bg-*, text-text-*, border-border-*), clases de componente (.btn-primary, .input, .label, .card), nunca hex hardcodeados ni text-white directo.
```

---

# Fase 4 — Compras + Inventario

### Bloque 4.1 — Backend stock_movements + stock_current

```
Implementar bloque 4.1 siguiendo docs/roadmap.md, docs/erd.md, CLAUDE.md y docs/common-patterns.md (sección lock pesimista).

- app/services/stock_service.py:
  - apply_movement(...) — la función completa del patrón en docs/common-patterns.md
  - get_current_stock(db, product_id, warehouse_id)
  - get_stock_summary(db, warehouse_id) — lista todos los productos con su stock actual
  - recalculate_stock_current() — script utilitario para reconstrucción
- app/api/stock.py:
  - GET /api/v1/stock?warehouse_id= — lista de stock actual
  - GET /api/v1/stock/movements?product_id=&warehouse_id=&date_from=&date_to= — historial
- scripts/recalculate_stock.py: comando standalone
- Tests críticos: CPP correcto en compras múltiples, lock pesimista funciona (test con asyncio concurrente), validación de stock negativo según setting

Este bloque es crítico. Plan mode obligatorio. Tests primero (TDD) si es posible.
```

### Bloque 4.2 — Backend compras

```
Implementar bloque 4.2 siguiendo docs/roadmap.md, docs/erd.md y CLAUDE.md.

- app/services/purchase_service.py:
  - create_purchase(db, data, user_id) — crea en draft
  - add_item, update_item, remove_item — solo en draft
  - confirm_purchase(db, purchase_id, user_id) — transacción atómica: cambio de estado + apply_movement por cada item (snapshot de quantity_base, exchange_rate, etc.)
  - cancel_purchase(db, purchase_id, user_id, reason) — solo si está confirmed, genera movements compensatorios
  - generate_purchase_number() — correlativo YYYY-NNNNNN
- app/api/purchases.py: CRUD + POST /purchases/{id}/confirm + POST /purchases/{id}/cancel
- Tests: confirm cambia stock y CPP correctamente, cancel genera compensación, no se puede confirmar dos veces

Plan mode obligatorio.
```

### Bloque 4.3 — UI lista de compras

```
Implementar bloque 4.3 siguiendo docs/roadmap.md.

- src/features/purchases/pages/PurchasesList.tsx: tabla con filtros (proveedor, fecha, estado)
- Badge de estado con color (gris=draft, verde=confirmed, rojo=cancelled)
- Click en fila → navega a detalle
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
- Botón "Cargar inventario inicial" → para cada fila con cantidad > 0, llama a apply_movement con movement_type=initial
- Validación: no permitir si ya hay movements para ese producto+warehouse
- Backend: endpoint POST /api/v1/stock/initial que recibe lista de items

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

- Configuración pytest con fixtures de BD de tests (transacción por test con rollback)
- Tests prioritarios:
  - stock_service: apply_movement (CPP, lock, stock negativo), recalculate
  - purchase_service: confirm (genera movements + actualiza stock), cancel (compensación)
  - sale_service: confirm (lock, snapshot de costo, validación de stock, pagos mixtos), cancel
  - settings_service: parseo de cada value_type
  - price_service: precio vigente con múltiples cambios de fecha
- Coverage objetivo ≥80% en services
- Documentar cómo correr tests en docs/comandos.md
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
Crear docs/deployment.md con guía completa de instalación en una PC nueva.

Incluir:
- Requisitos previos (Docker, Node, Python — si aplica fuera del contenedor)
- Clonado del repo y configuración de .env
- Instalación de dependencias
- Migración y seed inicial
- Configuración de rclone para backups (paso a paso con screenshots si es posible)
- Configuración de cron
- Configuración de IP fija en el router
- Importación del certificado mkcert en dispositivos del cliente
- Checklist de smoke test post-instalación
```

### Bloque 7.6 — Datos iniciales del cliente

```
Coordinar con el cliente carga inicial:
- Lista de productos con SKU, nombre, categoría, unidades, precios
- Lista de proveedores habituales
- Stock actual al momento de inicio
- Configuración inicial de settings (business_name, business_document, etc.)

Crear script de importación CSV en scripts/import_initial_data.py para productos en bulk si el cliente provee Excel/CSV.
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
