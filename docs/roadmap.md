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
  - Endpoints `GET /contacts`, `GET /contacts/{id}`, `POST /contacts`, `PUT /contacts/{id}`, `DELETE /contacts/{id}` (soft delete)
  - Filtros: `?type=customer|supplier|both`, `?search=`, paginación
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

**Entregable:** catálogo de productos completo. El cliente puede cargar todos sus productos con sus distintas unidades y precios. Aún no se ve stock real porque no hay compras todavía.

---

## Fase 4 — Compras + Inventario inicial

**Objetivo:** registrar compras. Al confirmar, el stock se actualiza correctamente con CPP. Esta fase activa el flujo de stock por primera vez.

**Bloques:**

- **4.1 — Backend stock_movements + stock_current**
  - Modelos
  - Service `stock_service.py` con funciones:
    - `apply_movement(movement)` — inserta movement + actualiza stock_current con lock pesimista, calcula CPP en ingresos
    - `get_current_stock(product_id, warehouse_id)`
    - `recalculate_stock_current()` — utilidad para reconstrucción desde movements
  - Endpoints `GET /stock?warehouse_id=`, `GET /stock/movements?product_id=`

- **4.2 — Backend compras**
  - Modelos `purchases` y `purchase_items`
  - Service `purchase_service.py` con:
    - `create_purchase()` — crea cabecera en draft
    - `add_item()`, `update_item()`, `remove_item()` — items en draft
    - `confirm_purchase()` — transacción atómica: confirma + genera movements + actualiza stock con CPP
    - `cancel_purchase()` — genera movimientos compensatorios
  - Generación de `purchase_number` correlativo
  - Endpoints CRUD + `POST /purchases/{id}/confirm`, `POST /purchases/{id}/cancel`

- **4.3 — UI lista de compras**
  - Página `/compras` con tabla, filtros por proveedor, fecha, estado
  - Indicador de estado (draft / confirmed / cancelled)

- **4.4 — UI formulario de compra**
  - Página `/compras/nueva` y `/compras/:id`
  - Selector de proveedor (autocomplete sobre `contacts`)
  - Selector de moneda + tipo de cambio (sugiere el vigente, editable)
  - Tabla de items: buscar producto, seleccionar unidad, cantidad, costo unitario, IVA
  - Cálculo en vivo de subtotal, IVA, total
  - Botones: Guardar como borrador / Confirmar / Cancelar
  - Al confirmar: confirmación visual con resumen de impacto en stock

- **4.5 — UI vista detalle de compra**
  - Página `/compras/:id` en modo lectura para compras confirmadas
  - Botón "Cancelar compra" con confirmación y motivo

- **4.6 — UI inventario inicial**
  - Funcionalidad para cargar stock inicial (sin compra real)
  - Usa `stock_movements` con `movement_type='initial'`
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
  - Modelos `stock_adjustments` y `stock_adjustment_items`
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
  - Exportación a CSV (decidir si v1 o se difiere)

**Entregable:** sistema completo funcionalmente. El cliente tiene visibilidad sobre el negocio: qué se vende, cuánto se gana, qué falta reponer.

---

## Fase 7 — Pulido y entrega

**Objetivo:** preparar el sistema para uso productivo en el local del cliente.

**Bloques:**

- **7.1 — Tests del backend**
  - Tests unitarios de services críticos: `stock_service` (lock, CPP, movements), `purchase_service` (confirm/cancel), `sale_service` (confirm/cancel, stock negativo, pagos mixtos)
  - Coverage objetivo: ≥80% en services, ignorar routers
  - Fixtures con BD de prueba y rollback por test

- **7.2 — Manejo de errores y validaciones finales**
  - Revisar todos los endpoints: códigos HTTP correctos, mensajes de error útiles, validaciones Pydantic completas
  - Frontend: manejo de errores de red, mensajes claros al usuario
  - Logs estructurados en backend (level INFO en producción)

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

- **7.5 — Documentación de deployment**
  - Documento `docs/deployment.md` con pasos para desplegar DTCore en una PC nueva
  - Script de instalación inicial (asume Ubuntu/Debian o documenta Windows con WSL)
  - Configuración de `rclone` paso a paso
  - Configuración de cron para backups y verificación

- **7.6 — Datos iniciales del cliente**
  - Cargar productos reales de Rincón de Embalajes (con cliente o pidiéndoselos)
  - Cargar proveedores habituales
  - Inventario inicial real

- **7.7 — Capacitación**
  - Sesión con el cliente para uso del POS
  - Documento corto de "atajos y trucos" impreso para tener a mano
  - Configuración de PWA instalada en sus dispositivos
  - Importación del certificado mkcert en celular y notebook del cliente

- **7.8 — Período de acompañamiento**
  - 3 meses de soporte según contrato
  - Backlog de mejoras detectadas en uso real → entran a v2

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
