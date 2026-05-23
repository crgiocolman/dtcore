# CLAUDE.md — Reglas del proyecto DTCore

DTCore es un sistema base de gestión de compra/venta/inventario para pequeños negocios. Producto reutilizable: el código es el mismo entre instalaciones, la configuración por cliente vive en `.env` y en la tabla `settings`.

**Stack y arquitectura confirmados.** El modelo de datos está en `docs/erd.md` y es fuente de verdad para el schema. Las decisiones de diseño en `docs/design-decisions.md` explican el porqué.

Para contexto extendido ver: `docs/design-decisions.md` (historial de por qué), `docs/common-patterns.md` (patrones de código), `docs/roadmap.md` (fases), `HANDOFF.md` (estado actual operativo).

---

## Stack

**Backend:** Python 3.12+ · FastAPI · SQLAlchemy 2.0 (async, asyncpg) · PostgreSQL 16 · Pydantic v2 · pydantic-settings · Alembic · uvicorn · bcrypt · python-jose (JWT) · python-multipart.

**Frontend:** React 18 + TypeScript · Vite 5 · Tailwind CSS 3 · React Router v6 · Zustand · Recharts · Workbox (PWA instalable, sin offline real).

**Infra:** Docker Compose en la PC-servidor del cliente (3 servicios: `db`, `api`, `web` con nginx). HTTPS local con mkcert. Sin deploy externo en v1.

**Backups:** `pg_dump` + `rclone` a Google Drive vía cron. Retención 30 días local / 90 días remoto.

---

## Arquitectura

- `Base` declarativa vive en `app/database.py`, no en `app/models/`
- Lógica de negocio en `app/services/`, nunca en `app/api/` (routers)
- Routers validan con Pydantic y delegan a services
- Schemas Pydantic obligatorios para todo endpoint con datos externos
- Seeds en `app/seed/` — datos iniciales: admin user, currencies (PYG/USD/BRL/ARS), warehouse default, settings, IVA rates
- Frontend: estado global en Zustand, estado de servidor en hooks custom con fetch directo (sin react-query en v1)
- Frontend: una carpeta `src/features/<modulo>/` por módulo funcional con `pages/`, `components/`, `hooks/`, `api/`

---

## Schema

Las reglas del schema están detalladas en `docs/erd.md`. Resumen de las que más se aplican durante codificación:

- **UUID v4 como PK en todas las tablas — generado en el cliente** (`crypto.randomUUID()` en frontend, soporte directo para POS con múltiples cajas en el futuro)
- **Enums como tipos nativos de PostgreSQL**, no strings con CHECK
- **Enums Python heredan de `(str, Enum)`**, miembros UPPERCASE, valores lowercase. Usar `values_callable=lambda obj: [e.value for e in obj]` en la columna SQLAlchemy
- **Timestamps con timezone siempre:** `DateTime(timezone=True)` / `TIMESTAMPTZ`
- **`datetime.now(timezone.utc)` en Python.** Nunca `datetime.utcnow()` (deprecated)
- **FKs con `ON DELETE RESTRICT`** por default. Borrados lógicos via `deleted_at`, no físicos
- **Todas las FKs, unique constraints e índices llevan nombre explícito** (`fk_<tabla>_<columna>`, `uq_<tabla>_<col>`, `ix_<tabla>_<columna>`)
- **Montos en `NUMERIC(18,4)`.** Nunca `FLOAT` ni `DECIMAL` sin precisión explícita. Justificación en `design-decisions.md`
- **Tipos de cambio en `NUMERIC(18,6)`** (más precisión que montos)
- **Auditoría:** `created_by_user_id`, `updated_by_user_id` en tablas transaccionales (mixin `AuditUserMixin`)

---

## Patrones obligatorios

- `logger` para errores en services, nunca `print`
- `print` solo debug temporal, eliminar antes de commit
- Toda función que modifique BD vive en service, no en router
- `db.rollback()` en except antes de retornar
- **Stock como ledger append-only:** `stock_movements` es inmutable. `stock_current` es cache desnormalizado que se actualiza en la misma transacción que el movement que la generó
- **Lock pesimista en escritura de stock:** `SELECT ... FOR UPDATE` sobre `stock_current` antes de cualquier UPDATE. Aplica en confirmación de venta, confirmación de compra, ajustes, devoluciones
- **Compras y ventas transaccionales:** la confirmación crea cabecera, items, payments (si aplica), movements y actualiza stock_current en una sola transacción. Si falla cualquier paso, rollback completo
- **Snapshots en items:** `unit_cost_base_at_sale`, `tax_rate`, `tax_included`, `quantity_base`, `exchange_rate` se copian al item al confirmar. No se referencian dinámicamente
- **Tipo de cambio snapshot:** la cabecera de compra/venta guarda el `exchange_rate` aplicado. Reportes históricos no cambian si después cambia la cotización
- **Precios históricos en `product_prices`:** append-only. Precio vigente = mayor `effective_from <= hoy` para `product_unit_id + currency_code`
- **CPP en compras:** `nuevo_avg = (stock_actual * avg_actual + qty_nueva * costo_nuevo) / (stock_actual + qty_nueva)`. Las salidas no afectan el avg
- **Settings clave-valor tipadas:** nuevas flags se agregan via seed, no via migración de columna

---

## Reglas de negocio (codificadas en services)

- **IVA Paraguay:** tasas 0% (exento), 5%, 10%. Default 10% en productos nuevos (configurable via settings)
- **Precio de góndola incluye IVA por default** (`tax_included_in_price = true`). El service calcula base imponible y IVA al confirmar venta
- **Stock negativo:** controlado por `settings.allow_negative_stock`. Si false, la venta aborta cuando `stock_current.quantity_base < quantity_base` solicitada
- **Multimoneda:** PYG es moneda base (hardcoded en `settings.default_currency_code`). Toda compra/venta guarda su moneda original y el `exchange_rate` snapshot. Reportes consolidados usan `total_base_currency`
- **Venta requiere cliente:** controlado por `settings.sale_requires_customer`. Default `false` (permite venta anónima)
- **Pagos mixtos:** `sale_payments` permite N filas por venta. Suma debe igualar `sales.total`
- **Devolución:** v1 se modela como `stock_movement` con `movement_type='return_in'` (de venta) o `'return_out'` (a proveedor). v2 formaliza `credit_notes`
- **Numeración correlativa interna** (`purchase_number`, `sale_number`, `adjustment_number`): generada por el backend al confirmar, no en draft. Formato sugerido: `YYYY-NNNNNN`

---

## Cancelaciones y compensaciones

- **Compra/venta confirmada no se borra, se cancela.** La cancelación genera movimientos compensatorios en `stock_movements` (`return_out` para compra cancelada, `return_in` para venta cancelada)
- **CPP no se recalcula hacia atrás** en cancelaciones. Se considera que el costo histórico se mantiene
- **`status = 'cancelled'`** + `cancelled_at` + `cancelled_reason` en cabecera

---

## Alembic

- Nunca DROP TABLE para agregar columnas
- Flujo: `alembic revision --autogenerate` → revisar el archivo → probar upgrade/downgrade/upgrade local → aceptar
- Alembic autogenerate tiene bugs conocidos: no emite ENUM DROP en downgrade, no siempre respeta orden de FKs entre tablas nuevas. Revisar siempre
- ADD COLUMN NOT NULL sobre tabla con datos: migración en 3 pasos (add nullable → backfill → alter not null)
- Seed data se ejecuta después de la primera migración, no dentro de ella
- Orden de creación inicial está en `docs/erd.md` sección final

---

## Configuración por cliente

DTCore es reutilizable. Lo específico de cada instalación NO va en el código:

- **`.env`:** `DATABASE_URL`, `STORAGE_PATH`, `JWT_SECRET`, `BACKUP_DRIVE_REMOTE_PATH`
- **Tabla `settings`:** `business_name`, `business_document`, `default_currency_code`, `allow_negative_stock`, `sale_requires_customer`, `default_tax_rate`, etc.
- **El frontend muestra `business_name` desde settings al lado del logo "DTCore"** — nunca hardcodear nombres de cliente en el código
- **Documentación de deployment específica del cliente** vive fuera del repo (no se versiona con el código del producto)

---

## Autenticación y roles

- **JWT con expiración configurable** (default: 8 horas). Refresh manual al loguear
- **Roles definidos pero sin UI de gestión en v1:** enum `user_role` con `admin` y `operator`. Seed crea un admin inicial
- **Decorador `require_role(role)`** disponible en services, no usado activamente en v1 — la base queda lista
- **Password hashing con bcrypt cost 12**

---

## Frontend — POS

- **El POS debe ser usable solo con teclado.** Mouse opcional, no obligatorio
- **Tab order del POS:** búsqueda producto → cantidad → unidad → Enter (agrega al carrito) → vuelve a búsqueda
- **Shortcuts globales del POS:**
  - `F1` — Ayuda / lista de shortcuts
  - `F2` — Seleccionar cliente
  - `F3` — Aplicar descuento (item o cabecera según contexto)
  - `F4` — Cobrar (abre modal de pagos)
  - `F9` — Cancelar venta en progreso (limpia carrito)
  - `Esc` — Limpiar campo activo
  - `↑/↓` — Navegar resultados de búsqueda
  - `Enter` — Seleccionar resultado / confirmar
- **Búsqueda de productos:** por SKU, barcode, o nombre (substring case-insensitive). Resultado con flechas + Enter
- **Sin modales bloqueantes en el flujo principal.** El carrito siempre visible a la derecha. Edición de cantidad inline

---

## Frontend — patrones generales

- **PWA instalable sin offline real.** Sin conexión al servidor, la app muestra "Sin conexión". No hay IndexedDB ni sync queue (a diferencia de TributarioPY)
- **HTTPS local con mkcert** necesario para que PWA funcione en celular del cliente. Instalar CA root en dispositivos del cliente durante capacitación
- **Acceso vía LAN:** la PC-servidor tiene IP fija. Dispositivos del cliente acceden por `https://<ip-lan>` desde el WiFi del local
- **Sin acceso desde fuera del local en v1.** Si se necesita en el futuro: Tailscale (no implementado todavía)

---

## Flujo de trabajo

1. Decisiones de diseño en Claude.ai, ejecución en Claude Code
2. Prompts a Claude Code referencian "siguiendo CLAUDE.md" en lugar de repetir reglas
3. Si Claude Code detecta que una regla contradice al código actual, o encuentra un caso no cubierto: parar y pedir clarificación. No improvisar. CLAUDE.md es fuente de verdad
4. Al terminar una tarea: resumen de 2-3 oraciones de qué cambió. Sin desglosar archivo por archivo salvo pedido explícito
5. Output de Claude Code se revisa antes de aceptar/commitear
6. **Nunca hacer `git commit` sin que el usuario lo pida explícitamente.** El usuario revisa y commitea manualmente

---

## Trabajando con Claude Code

**Plan Mode obligatorio** para tareas que tocan más de un archivo. Activar con `Shift + Tab`. Proponer plan escrito antes de editar.

**Ejecución directa permitida** solo para: fixes chicos (1 archivo, <50 líneas), renombrar variables, agregar logs/docstrings, ejecutar diseños ya validados en Claude.ai.

**Revisión de diffs — qué rechazar automáticamente:**

- Timestamps sin timezone o `datetime.utcnow()`
- `except Exception: pass` que silencia errores
- Nombres autogenerados de constraints/FKs
- Montos con FLOAT o DECIMAL sin precisión en lugar de `NUMERIC(18,4)`
- Lógica de negocio en routers en vez de services
- Actualización de stock sin `SELECT ... FOR UPDATE`
- Diff >150 líneas en un archivo — pedir partir en cambios más chicos
- UUID generado en el server cuando debería generarse en el cliente
- Hardcodear nombres de cliente ("Rincón de Embalajes", etc.) en código — usar `settings.business_name`
- Item de compra/venta sin snapshots de `quantity_base`, `exchange_rate`, `tax_rate`, `unit_cost_base_at_sale`

**Cuándo volver a Claude.ai:**

- Claude Code pregunta entre alternativas que afectan arquitectura
- Error cuya causa sospechás que es problema de diseño más profundo
- Acumulando deuda técnica por apuro

**Cuándo ir directo a Claude Code (sin diseño previo):**

- Renombrar una variable, agregar un log, arreglar un typo
- Fix de un bug trivial en un solo archivo
- Agregar un docstring o formatear código

**Comandos útiles:** `/clear` limpia contexto, `/compact` resume sesión, `think hard` / `ultrathink` en prompt aumenta thinking budget.

---

## Eficiencia de tokens

- Eliminar filler conversacional ("Certainly", "I hope this helps")
- No resumir el request ni explicar qué se va a hacer
- Partial updates only: proveer solo funciones/bloques que cambiaron, no archivos enteros
- Usar `// ... existing code ...` para indicar secciones sin cambios
- No re-declarar información ya presente en los archivos del proyecto o el chat
- Si la tarea es compleja: plan en 1-2 bullets antes de escribir código

---

## Retomar después de pausa

1. Leer `HANDOFF.md` primero
2. `git log --oneline -20` para últimos commits
3. Verificar entorno: `docker ps`, venv activado, `alembic current`
4. Abrir Claude Code en la raíz del proyecto (lee CLAUDE.md automático)

---

## Testing

- **Backend:** pytest con `pytest-asyncio`. Foco en services con lógica de negocio (stock, CPP, IVA, transacciones de compra/venta)
- **Frontend:** sin tests en v1 (foco en feedback manual con cliente)
- **Fixtures de BD:** transacción por test con rollback, DB de tests separada
