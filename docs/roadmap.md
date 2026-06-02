# docs/roadmap.md — Roadmap de DTCore

Fases organizadas verticalmente por módulo end-to-end (backend + frontend juntos). Cada fase es entregable independiente. La Fase 0 es horizontal porque establece la base sobre la que se construyen las fases verticales.

**Estado actual:** diseño cerrado, sin código todavía. Ver `HANDOFF.md` para estado operativo cuando empiece la ejecución.

---

## Fase 0 — Setup y fundaciones

**Objetivo:** entorno funcionando, schema completo en BD, layout del frontend con auth. No hay módulos de negocio todavía, pero todo lo necesario para construirlos está listo.

**Bloques:**

- **0.1 — Estructura del proyecto**
  - Carpetas `backend/` y `frontend/`, `.gitignore`, `README.md` mínimo, `docker-compose.yml` con PostgreSQL 16
  - Backend: estructura de carpetas (`app/api/`, `app/services/`, `app/models/`, `app/schemas/`, `app/seed/`), `requirements.txt`, venv, `pyproject.toml` con configuración de ruff/black
  - Frontend: Vite + React 18 + TS + Tailwind 3 + React Router v6 + Zustand + Recharts + Workbox, estructura `src/features/`, `src/components/`, `src/lib/`

- **0.2 — Base de SQLAlchemy + Alembic + settings**
  - `app/database.py` con `Base`, engine async, session factory
  - `app/config.py` con pydantic-settings (DATABASE_URL, JWT_SECRET, STORAGE_PATH, etc.)
  - Mixins reutilizables (`TimestampMixin`, `SoftDeleteMixin`, `AuditUserMixin`)
  - Alembic inicializado y configurado para async

- **0.3 — Schema completo (migración inicial)**
  - Todos los modelos de `docs/erd.md` definidos en `app/models/`
  - Enums en `app/enums.py`
  - Primera migración Alembic que crea las ~18 tablas en el orden definido en el ERD
  - Verificación: `alembic upgrade head` corre limpio en BD vacía

- **0.4 — Seeds iniciales**
  - Usuario admin inicial (password en variable de entorno o prompt)
  - Currencies: PYG, USD, BRL, ARS
  - Warehouse "Depósito principal" con `is_default=true`
  - Settings con todos los keys definidos en el ERD
  - Script `python -m app.seed.run` ejecutable

- **0.5 — Auth (backend + frontend)**
  - Backend: endpoints `/auth/login`, `/auth/me`, `/auth/logout`, hashing bcrypt, JWT con expiración 8h
  - Decorador `require_auth` para endpoints protegidos
  - Decorador `require_role(role)` definido aunque no se use activamente
  - Frontend: store Zustand de auth, hook `useAuth`, página `/login`, redirect a login si no hay token
  - Logout limpia token y redirige

- **0.6 — Layout del frontend**
  - AppLayout con header (logo "DTCore" + `business_name` desde settings + usuario logueado + logout) y sidebar de navegación
  - Rutas placeholder para todos los módulos futuros (cada una muestra "En construcción")
  - Página `/admin/settings` placeholder (se implementa en Fase 1)
  - Estilos base de Tailwind con paleta del proyecto

- **0.7 — HTTPS local y PWA básica**
  - `vite-plugin-mkcert` configurado, HTTPS funciona en `npm run dev` y `npm run preview`
  - PWA manifest básico (nombre "DTCore", iconos placeholder)
  - Workbox configurado para precachear assets del build (sin lógica offline custom)
  - Verificación: la app se puede "instalar" como PWA desde el browser

- **0.8 — Backups**
  - Script `backup.sh` que corre `pg_dump` + `rclone copy`
  - Documentación de configuración inicial de `rclone` con Drive
  - Script `verify_backup.sh` (verificación de existencia del dump del día)
  - Configuración de cron documentada (no instalada en código; se hace al desplegar)

**Entregable:** sistema corre, se puede loguear, se ve el layout vacío. Backups funcionando contra una cuenta de Drive de prueba. Base para que cualquier módulo siguiente se construya sobre.

---

## Fase 1 — Panel admin + Settings

**Objetivo:** el admin puede ver y modificar settings del sistema desde la UI. Esto se hace primero porque varios módulos siguientes dependen de settings configurables (`default_tax_rate`, `allow_negative_stock`, etc.).

**Bloques:**

- **1.1 — Service de settings**
  - `app/services/settings_service.py` con `get_setting(key)`, `set_setting(key, value)`, `get_all_settings()`
  - Serialización/deserialización según `value_type`
  - Cache en memoria con invalidación al escribir

- **1.2 — API de settings**
  - `GET /api/v1/settings` (lista todos)
  - `GET /api/v1/settings/{key}` (uno solo)
  - `PUT /api/v1/settings/{key}` (actualiza valor, valida tipo)
  - Solo accesible con rol `admin`

- **1.3 — UI panel admin**
  - Página `/admin/settings` con formulario agrupado por sección (Negocio, Moneda, Ventas, Stock)
  - Input apropiado según `value_type` (text, number, checkbox, etc.)
  - Validación cliente + backend
  - Toast de confirmación al guardar

- **1.4 — UI gestión de monedas**
  - Página `/admin/currencies`: lista de monedas activas/inactivas
  - Toggle activar/desactivar moneda
  - Formulario de carga de `exchange_rate` con fecha
  - Lista de tipos de cambio históricos (read-only)

**Entregable:** el cliente (o el desarrollador) puede configurar el sistema sin tocar BD directamente. Primer feedback útil del cliente: "el nombre del negocio se escribe así", "necesito agregar BRL como moneda".

---

## Fase 2 — Contactos

**Objetivo:** módulo de contactos completo. Necesario antes de compras (proveedores) y ventas (clientes).

**Bloques:**

- **2.1 — Backend contactos**
  - Modelo y schemas Pydantic
  - Service con CRUD + búsqueda por documento o nombre
  - Endpoints `GET /contacts`, `GET /contacts/{id}`, `POST /contacts`, `PATCH /contacts/{id}`, `DELETE /contacts/{id}` (soft delete)
  - Filtros: `?contact_type=customer|supplier|both`, `?search=`, paginación (`page`, `page_size`); `customer` y `supplier` incluyen registros `both`
  - Audit log al crear/actualizar/borrar

- **2.2 — UI lista de contactos**
  - Página `/contactos` con tabla, búsqueda, filtros por tipo
  - Paginación cliente o server-side (decidir en implementación)
  - Botón "Nuevo contacto"

- **2.3 — UI formulario de contacto**
  - Página `/contactos/nuevo` y `/contactos/:id`
  - Validaciones: business_name requerido, formato de email si se proporciona
  - Botón eliminar con confirmación

**Entregable:** módulo de contactos usable end-to-end. El cliente puede cargar sus proveedores y clientes habituales.

---

## Fase 3 — Productos (módulo crítico)

**Objetivo:** módulo de productos completo con soporte de múltiples unidades y precios. Es el módulo más complejo del sistema; vale la pena hacerlo antes de compras/ventas para que esté maduro cuando se use.

**Bloques:**

- **3.1 — Backend categorías**
  - Modelo `product_categories` con jerarquía
  - CRUD + endpoint para obtener árbol de categorías

- **3.2 — Backend productos**
  - Modelo `products` con todas las columnas del ERD
  - Service con CRUD + búsqueda (por SKU, barcode, nombre con trigram)
  - Habilitar extensión `pg_trgm` en migración
  - Endpoints CRUD + endpoint de búsqueda optimizada para POS (`GET /products/search?q=`)

- **3.3 — Backend unidades de producto**
  - Modelo `product_units` con CRUD anidado bajo productos
  - Validaciones: al menos una unidad con `factor_to_base=1`, solo una default de venta, solo una default de compra
  - Endpoints `GET /products/{id}/units`, `POST /products/{id}/units`, `PUT /products/{id}/units/{unit_id}`, `DELETE`

- **3.4 — Backend precios**
  - Modelo `product_prices` append-only
  - Service para obtener precio vigente por `product_unit_id + currency_code`
  - Endpoint `POST /products/{id}/units/{unit_id}/prices` (agregar nuevo precio)
  - Endpoint `GET /products/{id}/units/{unit_id}/prices` (histórico)

- **3.5 — UI lista de productos**
  - Página `/productos` con tabla, búsqueda, filtros por categoría
  - Indicador de stock actual (consulta a `stock_current` del default warehouse)
  - Indicador visual de stock bajo (rojo) cuando `quantity_base <= low_stock_threshold`

- **3.6 — UI formulario de producto**
  - Página `/productos/nuevo` y `/productos/:id`
  - Sección principal: SKU, nombre, descripción, categoría, base_unit, tax_rate, tax_included_in_price, track_stock
  - Sub-sección de unidades: tabla editable inline (agregar/editar/quitar unidades con su factor)
  - Sub-sección de precios: tabla con precio vigente por unidad+moneda + botón "Cambiar precio" que abre modal

- **3.7 — UI categorías**
  - Página `/admin/categorias` con árbol jerárquico
  - CRUD inline

- **3.8 — Catálogo de unidades** ✅ 2026-05-28
  - Nueva tabla `units_catalog` con enum `unit_type` y 12 seeds fijos
  - Migración Alembic: backfill `products.base_unit` → `base_unit_id` y `product_units.unit_name` → `unit_catalog_id`
  - Backend completo: service, API (`/api/v1/units`), seed, actualización de services y APIs de productos/unidades
  - Frontend: selectores de catálogo en `ProductForm.tsx`, nueva página `/admin/units`
  - Documentado en `design-decisions.md`: catálogo vs texto libre, data semi-maestra vs operativa

**Entregable:** catálogo de productos completo. El cliente puede cargar todos sus productos con sus distintas unidades y precios. Aún no se ve stock real porque no hay compras todavía.

---

## Fase 4 — Compras + Inventario inicial

**Objetivo:** registrar compras. Al confirmar, el stock se actualiza correctamente con CPP. Esta fase activa el ledger de stock por primera vez. Cualquier bug en lock pesimista, CPP o conversión de unidades aparece acá — vale la pena no apurar.

**Bloques:**

- **4.1 — Backend stock_movements + stock_current** ✅ 2026-05-29
  - Modelos (ya en schema inicial, verificar)
  - Service `stock_service.py` con funciones:
    - `apply_movement(...)` — inserta movement + actualiza stock_current con lock pesimista, calcula CPP en ingresos
    - `get_current_stock(product_id, warehouse_id=None)` — uno o todos los depósitos
    - `get_stock_summary(warehouse_id, filtros, paginación)` — lista paginada de productos con su stock actual
    - `get_movements(filtros, paginación)` — historial filtrable (usado por kardex y vista de compra/venta)
    - `apply_initial_inventory(items, warehouse_id, user_id)` — carga inventario inicial; rechaza productos con movements previos
    - `recalculate_stock_current(warehouse_id=None, product_id=None)` — utilidad para reconstrucción desde movements
  - Patrón obligatorio: items se procesan ordenados por `product_id` para prevenir deadlocks
  - Endpoints:
    - `GET /api/v1/stock?warehouse_id=&search=&low_stock_only=&page=&page_size=`
    - `GET /api/v1/stock/products/{product_id}` (stock en todos los depósitos)
    - `GET /api/v1/stock/movements?product_id=&warehouse_id=&date_from=&date_to=&page=&page_size=`
    - `POST /api/v1/stock/initial` (recibe lista de items + warehouse_id)
  - Script standalone `app/scripts/recalculate_stock.py`

- **4.2 — Backend compras** ✅ 2026-06-01
  - Modelos `purchases` y `purchase_items` (ya en schema inicial, verificar)
  - Service `purchase_service.py` con:
    - `create_purchase()` — crea cabecera en draft
    - `update_purchase()` — actualiza cabecera solo en draft
    - `list_purchases()` — lista paginada con JOIN a contacts
    - `get_purchase()` — cabecera + items + supplier hidratados
    - `add_item()`, `update_item()`, `remove_item()` — items solo en draft; calcula snapshots (quantity_base, unit_cost_base_currency, tax_rate, tax_included); recalcula totales de cabecera
    - `confirm_purchase()` — transacción atómica: cambio de estado + apply_movement por cada item (ordenado por product_id, anti-deadlock) + actualiza stock con CPP
    - `cancel_purchase()` — recibe motivo; genera movimientos compensatorios (CPP no se recalcula hacia atrás)
    - `generate_purchase_number()` — correlativo `YYYY-NNNNNN`, atómico bajo concurrencia
  - Audit log en create / update / confirm / cancel
  - Endpoints CRUD + items anidados + `POST /purchases/{id}/confirm` + `POST /purchases/{id}/cancel`

- **4.3 — UI lista de compras** ✅ 2026-06-01
  - Página `/compras` con tabla, filtros por proveedor, fecha, estado
  - Indicador de estado (draft / confirmed / cancelled)
  - Click en fila: si status=draft → modo edición; si confirmed/cancelled → modo lectura

- **4.4 — UI formulario de compra** ✅ 2026-06-01
  - Página `/compras/nueva` y `/compras/:id`
  - Selector de proveedor (autocomplete sobre `contacts`)
  - Selector de moneda + tipo de cambio (sugiere el vigente, editable)
  - Tabla de items: buscar producto, seleccionar unidad, cantidad, costo unitario, IVA
  - Cálculo en vivo de subtotal, IVA, total
  - Botones: Guardar como borrador / Confirmar / Cancelar
  - Al confirmar: confirmación visual con resumen de impacto en stock
  - Flujo: formulario en memoria → primer "Guardar como borrador" crea el draft en backend y redirige a `/compras/:id` → cambios posteriores son inmediatos sobre el draft

- **4.5 — UI vista detalle de compra** ✅ 2026-06-01
  - Página `/compras/:id` en modo lectura para compras confirmadas/canceladas
  - Botón "Cancelar compra" con modal y motivo obligatorio
  - Historial de auditoría: quién creó, confirmó y canceló la compra (con fecha y motivo)

- **4.6 — UI inventario inicial**
  - Funcionalidad para cargar stock inicial (sin compra real)
  - Consume el endpoint `POST /api/v1/stock/initial` ya creado en bloque 4.1
  - Página `/admin/inventario-inicial` con tabla de productos + input de cantidad y costo

**Entregable:** el cliente puede registrar compras reales y ver su stock acumularse. Primera medición útil del modelo de CPP. Si hay bugs en el cálculo, se detectan acá.

---

## Fase 5 — Ventas (POS)

**Objetivo:** punto de venta funcional y optimizado para teclado. El módulo más visible del sistema.

**Bloques:**

- **5.1 — Backend ventas**
  - Modelos `sales`, `sale_items`, `sale_payments`
  - Service `sale_service.py` con:
    - `create_sale()` — crea en draft (en POS se confirma directo)
    - `confirm_sale()` — transacción atómica con lock pesimista, validación de stock, snapshot de costos, generación de movements
    - `cancel_sale()` — genera movimientos compensatorios
  - Validación: suma de `sale_payments.amount` = `sales.total`
  - Validación: `customer_id` requerido si `settings.sale_requires_customer = true`
  - Generación de `sale_number` correlativo
  - Endpoints CRUD + confirm + cancel

- **5.2 — UI POS — layout principal**
  - Página `/pos` con layout dual: izquierda búsqueda + carrito, derecha resumen + cobro
  - Sin sidebar de navegación en esta página (pantalla completa)
  - Tab order definido en CLAUDE.md sección POS

- **5.3 — UI POS — búsqueda y carrito**
  - Campo de búsqueda con autocomplete (SKU, barcode, nombre)
  - Resultado seleccionable con flechas + Enter
  - Selector de unidad y cantidad inline
  - Carrito: lista de items con edición de cantidad inline (flechas o input directo)
  - Cálculo en vivo de subtotal, descuentos, IVA, total

- **5.4 — UI POS — cliente y descuentos**
  - F2 abre selector de cliente (autocomplete con búsqueda) — opcional según settings
  - F3 abre modal de descuento (item o cabecera, monto o porcentaje)
  - Mostrar cliente seleccionado en el resumen lateral

- **5.5 — UI POS — cobro y confirmación**
  - F4 abre modal de cobro
  - Permite pagos mixtos: agregar N pagos con método + monto + referencia
  - Validación: suma = total
  - Botón "Cobrar" → confirma venta, muestra confirmación visual, limpia carrito
  - F9 cancela venta en progreso

- **5.6 — UI lista de ventas**
  - Página `/ventas` con tabla, filtros por fecha, cliente, estado
  - Vista detalle (lectura) con opción de cancelar venta

- **5.7 — Shortcuts y accesibilidad**
  - F1 muestra modal de ayuda con todos los shortcuts
  - Indicador visual del foco actual (qué campo está activo)
  - Sonido opcional al confirmar venta (configurable en settings)

**Entregable:** POS funcional. El cliente puede empezar a operar con él. Acá es donde más feedback útil va a aparecer (orden de tabs, velocidad, claridad).

---

## Fase 6 — Ajustes de stock + reportes básicos

**Objetivo:** ajustes manuales de stock + dashboard con los reportes más importantes.

**Bloques:**

- **6.1 — Backend ajustes**
  - Modelos `stock_adjustments` y `stock_adjustment_
items`
  - Service con flujo draft → confirmed → cancelled
  - Confirmación genera movements + actualiza stock
  - Endpoints CRUD + confirm + cancel

- **6.2 — UI ajustes**
  - Página `/ajustes` con lista
  - Formulario de ajuste: selector de motivo, items con cantidad +/-, costo si aplica
  - Vista detalle

- **6.3 — Backend reportes**
  - Service `report_service.py` con funciones:
    - `sales_by_period(date_from, date_to, group_by)` — ventas por día/semana/mes
    - `top_products(date_from, date_to, limit)` — productos más vendidos
    - `profit_by_product(date_from, date_to)` — utilidad usando `unit_cost_base_at_sale`
    - `low_stock_products()` — productos bajo umbral
    - `stock_value()` — valor total de inventario al costo
    - `movements_by_product(product_id, date_from, date_to)` — kardex
  - Endpoints `/reports/*`

- **6.4 — UI dashboard (Home)**
  - Página `/` con:
    - Métricas del mes actual: ventas totales, cantidad de operaciones, ticket promedio, utilidad
    - Gráfico de barras: ventas por día del mes (Recharts)
    - Gráfico circular: top 10 productos vendidos del mes
    - Alertas: productos con stock bajo (lista con link a producto)
    - Métrica: valor de inventario actual

- **6.5 — UI página de reportes**
  - Página `/reportes` con selector de tipo de reporte + filtros
  - Reportes implementados: ventas por período, top productos, utilidad por producto, kardex de producto, valor de inventario
  - Exportación a CSV

**Entregable:** sistema completo funcionalmente. El cliente tiene visibilidad sobre el negocio: qué se vende, cuánto se gana, qué falta reponer.

---

## Fase 7 — Pulido y entrega

**Objetivo:** preparar el sistema para uso productivo en el local del cliente.

**Orden de ejecución recomendado:**

1. **7.2** primero — endurecer manejo de errores y códigos HTTP antes de testear, evita reescribir tests sobre comportamiento que va a cambiar.
2. **7.3 y 7.4** paralelizables — son frontend, no afectan tests de backend.
3. **7.1** después de 7.2 — tests sobre el comportamiento final, no sobre código intermedio.
4. **7.5 y 7.5b** — deployment, después de tener tests verdes.
5. **7.6** durante deployment — carga inicial del cliente.
6. **7.7** última semana antes de entrega — capacitación con sistema estable.
7. **7.8** post-entrega — soporte y acompañamiento.

La numeración refleja agrupación lógica (tests, errores, UI, deployment, gente), no secuencia temporal.

**Bloques:**

- **7.1 — Tests del backend (foco crítico)**
  - Setup mínimo: BD de tests `dtcore_test`, conftest con fixture de rollback por test
  - Tests obligatorios (caminos críticos del negocio):
    - `stock_service.apply_movement`: CPP correcto con compras múltiples del mismo producto, lock pesimista con `asyncio.gather`, stock negativo bloqueado/permitido según setting `allow_negative_stock`
    - `purchase_service.confirm`: cambia stock y CPP correctamente, compra en USD aplica conversión, no se confirma dos veces
    - `purchase_service.cancel`: genera movements compensatorios, CPP no se recalcula hacia atrás
    - `sale_service.confirm`: descuenta stock con lock, snapshot de costo correcto, valida `sum(payments) == total`
    - `sale_service.cancel`: devuelve stock
  - Tests de regresión: uno por cada bug encontrado durante QA real (Fases 4, 5 y 6), con docstring que referencie el bug
  - SIN tests para: settings, prices, adjustments, reports (cubiertos por QA manual o son código trivial)
  - SIN objetivo numérico de coverage. Foco en caminos críticos del negocio
  - Documentar comandos de ejecución en `docs/comandos.md`

- **7.2 — Manejo de errores y validaciones finales**
  - Auditoría sistemática: cada endpoint debe devolver código HTTP correcto y body estructurado (`{code, message, ...detalle}`), no solo `{detail: "Error"}`
  - Excepciones custom en `app/exceptions.py` con mapping consistente a HTTP
  - Frontend: helper `parseApiError` centraliza el manejo, con tests propios
  - Toast de error consistente, mensajes en español
  - Logs estructurados (level INFO en producción) en archivo configurable

- **7.3 — Sidebar colapsable**
  - Tres estados: expandido (~200px, default en escritorio), colapsado (~60px solo iconos), oculto
  - Botón en header para ciclar entre estados
  - Persistencia en `localStorage` de la preferencia del usuario
  - En POS (`/pos`) el sidebar está oculto automáticamente (ya cubierto en bloque 5.2)
  - Transición suave (200ms)

- **7.4 — Responsive básico para vista en celular**
  - Objetivo: el cliente puede consultar **reportes** desde el celular (fuera del local, en su WiFi). No optimizar para operar el sistema desde móvil
  - Breakpoint principal: `md` (768px)
  - En `< md`: sidebar se convierte en menú hamburguesa (drawer que se abre desde la izquierda)
  - Tablas con scroll horizontal cuando no caben
  - Dashboard (Home): cards apiladas verticalmente, gráficos full-width
  - Reportes: tabs scrollables, filtros colapsables
  - **POS, formularios de compra/venta, ajustes y catálogo NO se rediseñan para móvil en v1** — si se acceden desde celular, se ven en zoom de escritorio. Operación móvil real es v2.
  - Documentar la limitación en el README del cliente

- **7.5 — Documentación de deployment (Docker)**
  - Documento `docs/deployment.md` sección A: instalación con Docker Compose
  - Requisitos previos (Docker Desktop, Node, Python para venv)
  - Configuración de `.env`, build del frontend servido con `serve`
  - Configuración de `rclone` para backups paso a paso
  - Cron / Task Scheduler para backups diarios
  - Configuración de IP fija en router del cliente + importación de certificado mkcert
  - **Smoke test post-instalación**: lista de 15 verificaciones accionables (login, crear producto, compra, venta, dashboard, backup manual, reinicio de PC, acceso desde celular en LAN, F5 preserva ruta, cancelar venta)
  - Plan de rollback con `pg_restore`
  - Procedimiento de actualizaciones (`git pull` + migraciones + reinicio + smoke test reducido)

- **7.5b — Deployment nativo en Windows (sin Docker)**
  - Documento `docs/deployment.md` sección B: instalación nativa para clientes sin virtualización o con PCs de bajos recursos
  - Instalación de Python 3.12+, Node 20+, PostgreSQL 16 nativo, Git
  - Setup de PostgreSQL nativo (usuario, BD, password)
  - Backend con venv + uvicorn; frontend con `npm run build` + `serve`
  - Arranque automático con NSSM como servicios de Windows: `dtcore-backend`, `dtcore-frontend` (PostgreSQL ya viene como servicio)
  - Backups con `pg_dump.exe` + `rclone.exe` ejecutados desde script PowerShell programado en Task Scheduler
  - Configuración de logs en `C:\dtcore\logs\`
  - Configuración de firewall de Windows (puertos 8000 backend, 4173 frontend)
  - Smoke test idéntico al de sección A
  - Plan de rollback y procedimiento de actualizaciones específicos para Windows
  - **Dry-run obligatorio:** antes del deployment real en cliente, instalar de cero en máquina del desarrollador siguiendo el manual, reiniciar PC, ejecutar smoke test, simular corte de luz

- **7.6 — Datos iniciales del cliente**
  - Crear templates CSV: `products_template.csv`, `contacts_template.csv`, `initial_inventory_template.csv` con headers en español y filas de ejemplo
  - Crear `app/scripts/import_initial_data.py` con flag `--dry-run` que valida primero (SKUs únicos, categorías existentes, unidades del catálogo, tipos válidos) y reporta errores sin importar
  - Si validación OK: importa todo en transacción atómica
  - Orden de carga documentado: catálogo de unidades (seed) → categorías → productos → contactos → inventario inicial
  - Proceso con cliente: enviar templates → cliente llena en Excel/Sheets → exporta CSV UTF-8 → `--dry-run` → importar → smoke test

- **7.7 — Capacitación**
  - Agenda de 2-3 horas dividida en bloques: POS (45 min), compras (30 min), productos (30 min), reportes (20 min), backup y emergencias (15 min)
  - Tareas prácticas durante la sesión: el cliente hace una compra real, una venta real con su POS, busca un producto, ve un reporte
  - Documento corto "atajos y trucos" impreso para tener a mano
  - Documento "qué hacer si..." de 1 página: WiFi caído, PC apagada, producto que no aparece, error en venta — las 10 preguntas más probables con respuesta corta
  - Instalación de PWA en dispositivos del cliente + importación del certificado mkcert en cada uno

- **7.8 — Período de acompañamiento**
  - 3 meses de soporte según contrato
  - Canal de comunicación único definido (sugerido: WhatsApp para este perfil de cliente)
  - Changelog interno con cada issue reportado
  - Cada bug crítico → fix inmediato con su test de regresión
  - Cada feature request → evaluar si es v1 (incluido) o v2 (cotizable aparte)
  - Revisión semanal de logs y backups durante el primer mes

**Entregable:** sistema en producción en el local del cliente. Cliente capacitado. Backups verificados. Listos para iterar.

---

## Versión 2 — Planificadas

Funcionalidades difereidas explícitamente del MVP. Se cotizan y priorizan según necesidad real del cliente después del primer trimestre de uso.

- **Comprobantes internos:** ticket/remito imprimible para entregar al cliente (sin timbrado)
- **Multi-depósito:** UI para gestionar `warehouses`, transferencias entre depósitos
- **Caja y turnos:** apertura/cierre de caja, arqueo, movimientos de caja
- **Notas de crédito:** formalizar devoluciones como documento
- **Listas de precios:** mayorista, minorista, descuentos por cliente
- **Roles y permisos:** UI de gestión de usuarios, restricciones por rol
- **Cuentas corrientes:** clientes y proveedores con saldo, pagos a cuenta
- **Acceso desde fuera de la LAN:** Tailscale o deploy a nube (Railway/Hetzner)
- **Mobile-first para operación:** POS rediseñado para touch, formularios optimizados para celular, bottom navigation. Permite que el cliente registre ventas desde celular sin compromiso de UX.

---

## Versión 3 — Futuro

- **Facturación electrónica SET:** timbrado, punto de expedición, CDC, QR, integración con SIFEN
- **Lotes y vencimientos:** trackeo por lote para productos perecederos o con vencimiento
- **FIFO opcional:** alternativa al CPP para clientes que lo necesiten
- **Integraciones contables:** exportación a sistemas tributarios paraguayos
- **App móvil nativa:** si la PWA no alcanza

---

## Cómo usar este roadmap

- Cada bloque (ej. 4.2) es una unidad de trabajo para una sesión de Claude Code con plan mode
- El prompt típico es: "Implementar bloque 4.2 siguiendo CLAUDE.md y docs/erd.md"
- Al terminar un bloque: actualizar `HANDOFF.md` con el cierre
- Si un bloque resulta más grande de lo previsto, partir en sub-bloques sobre la marcha
- Si surge una decisión nueva durante un bloque, parar y volver a Claude.ai antes de improvisar
