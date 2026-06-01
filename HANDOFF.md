# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-06-01 — Fase 5 cerrada (ventas + POS completo).

---

## Fase actual

**Fase 5 completa.** Próximo: **Fase 6 — Ajustes de stock + reportes básicos**, comenzando por **Bloque 6.1 — Backend ajustes** (`stock_adjustments`, `stock_adjustment_items`, draft→confirm→cancel).

---

## Estado del diseño

Toda la documentación de diseño está cerrada. Los docs vivos son `HANDOFF.md` (este), `docs/common-patterns.md` (se llena reactivamente), y `docs/design-decisions.md` (se agrega al tomar decisiones nuevas).

---

## Estado del código

- Backend completo hasta ventas: stock + CPP, compras draft→confirm→cancel, ventas draft→confirm→cancel con lock pesimista, validación de pagos, `sale_number` correlativo. `SaleItemOut` devuelve `product_name` y `unit_name` hidratados via JOIN.
- Frontend: layout dark mode, auth, admin completo (settings, currencies, categorías, unidades, inventario inicial), contacts, productos, **compras** (`/compras`, `/compras/:id`), **POS** (`/pos`) full-screen con carrito, atajos F1–F9, pagos mixtos, mensaje de error de stock detallado. **Ventas** (`/ventas`) con tabla paginada, filtros, modal de detalle (items + pagos + totales) y cancelación con motivo.
- `src/lib/hooks/useKeyboardShortcuts.ts` — hook global de atajos reutilizable.
- Migración `d056943fbd91` aplicada: `sale_number` nullable (asignado al confirmar, no al crear draft).
- Migraciones aplicadas hasta head actual. Ver `alembic current`.

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

**Bloque 6.1 — Backend ajustes de stock.** Modelos `stock_adjustments` y `stock_adjustment_items`, service con draft→confirm→cancel, confirmación genera `stock_movements` + actualiza `stock_current`, endpoints CRUD + confirm + cancel. Motivos de ajuste: enum o texto libre (decidir en diseño).

---

## Historial de fases

### Fase 5 — Ventas (POS) (cerrada 2026-06-01)

**5.1 — Backend ventas:** `sale_service.py` con draft→confirm→cancel. `confirm_sale` transacción atómica (lock pesimista, snapshot de costos, movements, `sale_number` correlativo). `cancel_sale` genera `return_in` compensatorios. `PaymentSumMismatchError` valida que suma de pagos = total. `sale_number` nullable hasta confirmación (migración `d056943fbd91`).

**5.2–5.5 — POS:** pantalla full-screen sin sidebar. Búsqueda de productos (SKU/barcode/nombre, debounce 200ms), carrito con edición inline, cálculo en vivo (IVA incluido/excluido), selector de cliente (F2), descuentos item y cabecera (F3), pagos mixtos (F4) con validación suma=total. Error de stock insuficiente muestra producto + disponible + solicitado.

**5.6 — Lista de ventas:** `/ventas` con tabla paginada, filtros (estado, cliente, fechas), modal de detalle con items (product_name hidratado via JOIN), pagos y totales, botón "Cancelar venta" con motivo obligatorio (`.btn-danger`). `SaleItemOut` extendido con `product_name` y `unit_name`.

**5.7 — Shortcuts:** `useKeyboardShortcuts` hook reutilizable en `src/lib/hooks/`. F1–F9 en POS, F1 abre modal de ayuda. Sonido al confirmar venta diferido a Fase 7.

### Fase 4 — Compras + Inventario, Bloques 4.1–4.6 (cerrado 2026-06-01)

**4.1 — Backend stock:** ledger append-only (`stock_movements`) + cache `stock_current` con lock pesimista (`SELECT FOR UPDATE`). CPP en entradas, stock negativo controlado por settings. `apply_initial_inventory` two-pass anti-deadlock. Script `recalculate_stock.py`.

**4.2 — Backend compras:** `purchase_service.py` con draft→confirm→cancel. `confirm_purchase` es transacción atómica (estado + movements ordenados por product_id + CPP). `cancel_purchase` genera `return_out` compensatorios. `generate_purchase_number` correlativo `YYYY-NNNNNN` con retry-on-IntegrityError. Audit log en create/update/confirm/cancel.

**4.3 — UI lista:** `/compras` con tabla paginada, filtros, badges de estado, click a formulario.

**4.4 — UI formulario:** `/compras/nueva` + `/compras/:id`. Autocomplete de proveedor y producto, IVA editable por ítem al agregar (inmutable en ítems guardados — snapshot), selector de moneda con TC sugerido, cálculo en vivo. Flujo en memoria → "Guardar borrador" → PATCH inmediato. Modal de confirmación con resumen de stock. `useItemFormShortcuts` (Enter/Esc), `formatQuantity`, `formatExchangeRate`.

**4.5 — UI detalle/cancelación + audit log:** modo lectura para confirmed/cancelled, `CancelPurchaseModal` con motivo obligatorio (`.btn-danger`), sección "Historial" con timeline de create/confirm/cancel (quién + cuándo + motivo si aplica). Endpoint `GET /purchases/{id}/audit` agregado al backend.

**4.6 — UI inventario inicial:** página `/admin/inventario-inicial` con tabla de productos (`track_stock=true`), inputs de cantidad + costo, llama a `POST /api/v1/stock/initial`. Detecta 409 por productos con movimientos previos.

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
