# docs/erd.md — Modelo de datos Rincón de Embalajes

Modelo de datos del sistema de compra/venta/inventario. Fuente de verdad para el schema de PostgreSQL.

**Versión:** v1 (MVP)
**Última actualización:** 2026-05-22

---

## Convenciones globales

Aplican a todas las tablas salvo que se indique lo contrario.

- **PK:** UUID v4, generado en el cliente (`crypto.randomUUID()` en frontend). Tipo `UUID` en PostgreSQL.
- **Timestamps:**
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` con trigger ON UPDATE
- **Soft delete:** `deleted_at TIMESTAMPTZ NULL` en tablas transaccionales y catálogos editables. Queries por default filtran `WHERE deleted_at IS NULL`.
- **Auditoría de usuario:** `created_by_user_id UUID NULL` y `updated_by_user_id UUID NULL` (FK a `users`) en tablas transaccionales (compras, ventas, ajustes, precios). No aplica a `audit_log` ni a tablas de catálogo puro como `currencies`.
- **Montos:** `NUMERIC(18,4)`. Justificación en `design-decisions.md`. La presentación se redondea según la moneda (`currencies.decimal_places`).
- **Tipos de cambio:** `NUMERIC(18,6)` (más precisión que montos).
- **FKs:** `ON DELETE RESTRICT` por default. Nombradas como `fk_<tabla>_<columna>`.
- **Unique constraints:** Nombradas como `uq_<tabla>_<col>` o `uq_<tabla>_<col1>_<col2>`.
- **Índices:** Nombrados como `ix_<tabla>_<columna>`.
- **Enums:** Tipos nativos PostgreSQL. En Python heredan de `(str, Enum)`, miembros UPPERCASE, valores lowercase. Usar `values_callable=lambda obj: [e.value for e in obj]` en la columna SQLAlchemy.

---

## Mixins reutilizables (SQLAlchemy)

```python
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class AuditUserMixin:
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
```

---

## Módulo 1 — Autenticación y configuración

### 1.1 `users`

Usuarios del sistema. En v1 solo se crea un admin desde seed; UI de gestión llega en v2.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `username` | VARCHAR(50) | NOT NULL, UNIQUE | `uq_users_username` |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt cost 12 |
| `full_name` | VARCHAR(150) | NOT NULL | |
| `email` | VARCHAR(150) | NULL | |
| `role` | ENUM `user_role` | NOT NULL, DEFAULT `'operator'` | |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `last_login_at` | TIMESTAMPTZ | NULL | |
| `created_at`, `updated_at`, `deleted_at` | — | TimestampMixin + SoftDeleteMixin | |

**Enum `user_role`:** `admin`, `operator`

**Índices:**
- `ix_users_username` (implícito por UNIQUE)
- `ix_users_is_active`

---

### 1.2 `settings`

Configuración del sistema como key-value tipada. Permite agregar flags sin migraciones.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `key` | VARCHAR(100) | PK | snake_case |
| `value` | TEXT | NOT NULL | Serializado según `value_type` |
| `value_type` | ENUM `setting_value_type` | NOT NULL | |
| `description` | TEXT | NULL | Para UI de admin |
| `updated_at` | TIMESTAMPTZ | NOT NULL, ON UPDATE NOW() | |
| `updated_by_user_id` | UUID | FK users, NULL | |

**Enum `setting_value_type`:** `string`, `int`, `decimal`, `bool`, `json`

**Seeds iniciales:**

| key | value_type | default | descripción |
|---|---|---|---|
| `business_name` | string | "Rincón de Embalajes" | Nombre del negocio |
| `business_document` | string | "" | RUC o documento del negocio |
| `default_currency_code` | string | "PYG" | Moneda base del sistema |
| `allow_negative_stock` | bool | false | Permite vender sin stock suficiente |
| `default_warehouse_id` | string | (UUID del depósito principal) | Depósito por defecto en POS |
| `low_stock_default_threshold` | decimal | 5 | Umbral default para alerta stock bajo |
| `sale_requires_customer` | bool | false | Si false, permite venta anónima |
| `default_tax_rate` | decimal | 10 | Tasa de IVA por defecto al crear productos |

---

### 1.3 `audit_log`

Registro de cambios sobre entidades transaccionales. Append-only.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK users, NOT NULL | Quién hizo el cambio |
| `entity_type` | VARCHAR(50) | NOT NULL | "sale", "purchase", "product", etc. |
| `entity_id` | UUID | NOT NULL | ID del registro afectado |
| `action` | ENUM `audit_action` | NOT NULL | |
| `changes` | JSONB | NULL | Diff de campos en updates `{campo: {from, to}}` |
| `ip_address` | VARCHAR(45) | NULL | IPv4/IPv6 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Enum `audit_action`:** `create`, `update`, `delete`, `restore`, `confirm`, `cancel`

**Índices:**
- `ix_audit_log_entity` (`entity_type`, `entity_id`)
- `ix_audit_log_user_id`
- `ix_audit_log_created_at`

**Sin** `updated_at` ni `deleted_at`. Append-only.

---

## Módulo 2 — Monedas

### 2.1 `currencies`

Catálogo de monedas soportadas.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `code` | VARCHAR(3) | PK | ISO 4217 (PYG, USD, BRL, ARS, EUR) |
| `name` | VARCHAR(50) | NOT NULL | "Guaraní paraguayo" |
| `symbol` | VARCHAR(5) | NOT NULL | "Gs", "$", "€" |
| `decimal_places` | SMALLINT | NOT NULL | 0 para PYG, 2 para USD |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `created_at`, `updated_at` | — | TimestampMixin | |

**Seeds iniciales:** PYG (0 decimales, "Gs"), USD (2 decimales, "$"), BRL (2 decimales, "R$"), ARS (2 decimales, "$").

---

### 2.2 `exchange_rates`

Histórico de tipos de cambio respecto a la moneda base (PYG).

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `currency_code` | VARCHAR(3) | FK currencies, NOT NULL | |
| `rate_to_base` | NUMERIC(18,6) | NOT NULL | Cuántos PYG = 1 unidad de la moneda |
| `effective_date` | DATE | NOT NULL | Fecha desde la que aplica |
| `notes` | TEXT | NULL | "Cotización BCP mediodía", etc. |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `created_by_user_id` | UUID | FK users, NULL | |

**Constraints:**
- UNIQUE(`currency_code`, `effective_date`) → `uq_exchange_rates_currency_date`

**Índices:**
- `ix_exchange_rates_lookup` (`currency_code`, `effective_date DESC`)

**Lógica:** El tipo de cambio vigente para una fecha X es el de mayor `effective_date <= X` para esa moneda. PYG no tiene registros (es la base, rate = 1 implícito).

---

## Módulo 3 — Contactos

### 3.1 `contacts`

Tabla única para clientes y proveedores. Un contacto puede ser ambos.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `contact_type` | ENUM `contact_type` | NOT NULL | |
| `document_type` | ENUM `document_type` | NOT NULL, DEFAULT `'none'` | |
| `document_number` | VARCHAR(30) | NULL | |
| `business_name` | VARCHAR(200) | NOT NULL | Razón social o nombre completo |
| `trade_name` | VARCHAR(200) | NULL | Nombre fantasía |
| `phone` | VARCHAR(30) | NULL | |
| `email` | VARCHAR(150) | NULL | |
| `address` | TEXT | NULL | |
| `notes` | TEXT | NULL | |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |
| `created_by_user_id`, `updated_by_user_id` | — | AuditUserMixin | |

**Enum `contact_type`:** `customer`, `supplier`, `both`
**Enum `document_type`:** `ruc`, `ci`, `passport`, `none`

**Índices:**
- `ix_contacts_document_number` (parcial: `WHERE document_number IS NOT NULL`)
- `ix_contacts_business_name`
- `ix_contacts_contact_type`

**Sin** UNIQUE sobre `document_number`. Duplicados se resuelven con merge manual en v2.

---

## Módulo 4 — Productos

### 4.1 `product_categories`

Categorías jerárquicas de productos.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `name` | VARCHAR(100) | NOT NULL | |
| `parent_id` | UUID | FK product_categories, NULL | Auto-referencia jerárquica |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |

**Constraints:**
- UNIQUE(`name`, `parent_id`) → `uq_product_categories_name_parent` (no permite hermanos con mismo nombre)

**Índices:**
- `ix_product_categories_parent_id`

---

### 4.2 `products`

Productos del catálogo. El stock se trackea en `base_unit`.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `sku` | VARCHAR(50) | NOT NULL, UNIQUE | Código interno |
| `barcode` | VARCHAR(50) | NULL | EAN/UPC del producto base |
| `name` | VARCHAR(200) | NOT NULL | |
| `description` | TEXT | NULL | |
| `category_id` | UUID | FK product_categories, NULL | |
| `base_unit` | VARCHAR(20) | NOT NULL | "unidad", "kg", "metro", "litro" |
| `track_stock` | BOOLEAN | NOT NULL, DEFAULT TRUE | False = servicio sin stock |
| `tax_rate` | NUMERIC(5,2) | NOT NULL, DEFAULT 10.00 | Tasa IVA: 0, 5, 10 |
| `tax_included_in_price` | BOOLEAN | NOT NULL, DEFAULT TRUE | Precio de góndola incluye IVA |
| `low_stock_threshold` | NUMERIC(18,4) | NULL | Override del default de settings |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |
| `created_by_user_id`, `updated_by_user_id` | — | AuditUserMixin | |

**Constraints:**
- UNIQUE(`sku`) → `uq_products_sku`
- CHECK(`tax_rate >= 0 AND tax_rate <= 100`) → `ck_products_tax_rate_range`

**Índices:**
- `ix_products_sku` (implícito por UNIQUE)
- `ix_products_barcode` (parcial: `WHERE barcode IS NOT NULL`)
- `ix_products_name` (para búsqueda con LIKE/trigram)
- `ix_products_category_id`
- `ix_products_is_active`

**Sugerencia:** habilitar extensión `pg_trgm` y crear índice GIN sobre `name` para búsqueda fuzzy en el POS.

---

### 4.3 `product_units`

Unidades de venta/compra del producto. Cada producto tiene N unidades, todas convertibles a `base_unit`.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `product_id` | UUID | FK products, NOT NULL, ON DELETE CASCADE | |
| `unit_name` | VARCHAR(30) | NOT NULL | "unidad", "rollo", "caja", "docena" |
| `factor_to_base` | NUMERIC(18,6) | NOT NULL | 1 rollo = 50 metros → factor 50 |
| `is_default_sale_unit` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `is_default_purchase_unit` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `barcode` | VARCHAR(50) | NULL | Código de barras propio (ej. la caja tiene EAN distinto) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `created_at`, `updated_at` | — | TimestampMixin | |

**Constraints:**
- UNIQUE(`product_id`, `unit_name`) → `uq_product_units_product_unit_name`
- CHECK(`factor_to_base > 0`) → `ck_product_units_factor_positive`

**Índices:**
- `ix_product_units_product_id`
- `ix_product_units_barcode` (parcial: `WHERE barcode IS NOT NULL`)

**Reglas de negocio:**
- Todo producto con `track_stock=true` debe tener al menos una `product_unit` con `factor_to_base=1` (la unidad base).
- Solo una unidad puede tener `is_default_sale_unit=true` por producto. Validación en service, no por constraint (parcial unique en PG es complejo).
- Mismo para `is_default_purchase_unit`.
- `ON DELETE CASCADE` aplica solo si el producto se borra físicamente (no debería pasar — usar soft delete).

---

### 4.4 `product_prices`

Histórico de precios de venta. Append-only.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `product_unit_id` | UUID | FK product_units, NOT NULL | |
| `currency_code` | VARCHAR(3) | FK currencies, NOT NULL | |
| `price` | NUMERIC(18,4) | NOT NULL | En la moneda indicada |
| `effective_from` | DATE | NOT NULL | |
| `notes` | TEXT | NULL | "Aumento por inflación", etc. |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `created_by_user_id` | UUID | FK users, NULL | |

**Constraints:**
- UNIQUE(`product_unit_id`, `currency_code`, `effective_from`) → `uq_product_prices_unit_currency_date`
- CHECK(`price >= 0`) → `ck_product_prices_non_negative`

**Índices:**
- `ix_product_prices_lookup` (`product_unit_id`, `currency_code`, `effective_from DESC`)

**Lógica:** Precio vigente = registro con mayor `effective_from <= hoy` para la combinación `product_unit_id + currency_code`. Sin `deleted_at`: precios viejos se mantienen para no romper reportes históricos.

---

## Módulo 5 — Inventario

### 5.1 `warehouses`

Depósitos. En v1 hay un solo registro `is_default=true`. UI de gestión llega en v2.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `name` | VARCHAR(100) | NOT NULL | |
| `description` | TEXT | NULL | |
| `is_default` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |

**Constraints:**
- Índice parcial único: `CREATE UNIQUE INDEX uq_warehouses_one_default ON warehouses (is_default) WHERE is_default = true AND deleted_at IS NULL` → solo un depósito default activo

**Seed inicial:** Un registro "Depósito principal" con `is_default=true`.

---

### 5.2 `stock_movements`

**Ledger append-only — fuente de verdad del stock.** Cada movimiento es inmutable.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `product_id` | UUID | FK products, NOT NULL | |
| `warehouse_id` | UUID | FK warehouses, NOT NULL | |
| `movement_type` | ENUM `stock_movement_type` | NOT NULL | |
| `direction` | ENUM `stock_direction` | NOT NULL | `in` / `out` |
| `quantity_base` | NUMERIC(18,4) | NOT NULL | Siempre en `base_unit`, siempre positivo |
| `unit_cost_base` | NUMERIC(18,4) | NULL | Costo unitario en PYG (moneda base). Obligatorio si `direction=in` |
| `reference_type` | ENUM `stock_reference_type` | NULL | Documento que originó el movimiento |
| `reference_id` | UUID | NULL | ID del documento (purchase, sale, adjustment) |
| `notes` | TEXT | NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `created_by_user_id` | UUID | FK users, NULL | |

**Enums:**
- `stock_movement_type`: `purchase`, `sale`, `return_in`, `return_out`, `adjustment_in`, `adjustment_out`, `initial`
- `stock_direction`: `in`, `out`
- `stock_reference_type`: `purchase`, `sale`, `adjustment`

**Constraints:**
- CHECK(`quantity_base > 0`) → `ck_stock_movements_quantity_positive`
- CHECK(`direction = 'out' OR unit_cost_base IS NOT NULL`) → `ck_stock_movements_cost_required_on_in`

**Índices:**
- `ix_stock_movements_product_warehouse` (`product_id`, `warehouse_id`, `created_at`)
- `ix_stock_movements_reference` (`reference_type`, `reference_id`)
- `ix_stock_movements_created_at`

**Sin** `updated_at` ni `deleted_at`. Append-only. Una corrección genera un nuevo movimiento compensatorio.

---

### 5.3 `stock_current`

**Cache desnormalizado** del stock actual por producto+depósito. Se actualiza en la misma transacción que el `stock_movement` que la genera, con `SELECT ... FOR UPDATE` (lock pesimista).

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `product_id` | UUID | FK products, NOT NULL | |
| `warehouse_id` | UUID | FK warehouses, NOT NULL | |
| `quantity_base` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Stock actual en `base_unit` |
| `avg_cost_base` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | CPP en moneda base (PYG) |
| `last_movement_at` | TIMESTAMPTZ | NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**PK:** Compuesta (`product_id`, `warehouse_id`)

**Cálculo de CPP en compras (ingreso):**
```
nuevo_avg = (stock_actual * avg_actual + qty_nueva * costo_nuevo) / (stock_actual + qty_nueva)
```

**Salidas:** El `avg_cost_base` no cambia. Se usa el valor vigente para calcular costo de venta en `sale_items.unit_cost_base_at_sale`.

**Reconstrucción:** Script `recalculate_stock.py` que itera `stock_movements` cronológicamente y reconstruye `stock_current` desde cero. Útil para detectar inconsistencias o reparar.

---

### 5.4 `stock_adjustments` + `stock_adjustment_items`

Ajustes manuales de inventario (conteo, mermas, correcciones).

**`stock_adjustments`**

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `adjustment_number` | VARCHAR(30) | NOT NULL, UNIQUE | Correlativo |
| `warehouse_id` | UUID | FK warehouses, NOT NULL | |
| `adjustment_date` | DATE | NOT NULL | |
| `reason` | ENUM `adjustment_reason` | NOT NULL | |
| `status` | ENUM `adjustment_status` | NOT NULL, DEFAULT `'draft'` | |
| `notes` | TEXT | NULL | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |
| `created_by_user_id`, `updated_by_user_id` | — | AuditUserMixin | |

**Enums:**
- `adjustment_reason`: `inventory_count`, `damage`, `loss`, `expired`, `correction`, `other`
- `adjustment_status`: `draft`, `confirmed`, `cancelled`

**`stock_adjustment_items`**

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `adjustment_id` | UUID | FK stock_adjustments, NOT NULL, ON DELETE CASCADE | |
| `product_id` | UUID | FK products, NOT NULL | |
| `product_unit_id` | UUID | FK product_units, NOT NULL | |
| `quantity` | NUMERIC(18,4) | NOT NULL | En unidad seleccionada (puede ser negativo) |
| `quantity_base` | NUMERIC(18,4) | NOT NULL | Convertido a base (signo conservado) |
| `direction` | ENUM `stock_direction` | NOT NULL | `in` (ingreso) o `out` (egreso) |
| `unit_cost_base` | NUMERIC(18,4) | NULL | Solo para `direction=in` |
| `notes` | TEXT | NULL | |

**Flujo:** crear como `draft`, agregar items, confirmar → genera `stock_movements` con `movement_type='adjustment_in'` o `'adjustment_out'` Y actualiza `stock_current`. Cancelar confirmado → genera movimientos compensatorios.

---

## Módulo 6 — Compras

### 6.1 `purchases`

Compras a proveedores.

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `purchase_number` | VARCHAR(30) | NOT NULL, UNIQUE | Correlativo interno |
| `supplier_id` | UUID | FK contacts, NOT NULL | |
| `supplier_document_number` | VARCHAR(30) | NULL | Nº de factura/ticket del proveedor |
| `purchase_date` | DATE | NOT NULL | |
| `warehouse_id` | UUID | FK warehouses, NOT NULL | Depósito que recibe |
| `currency_code` | VARCHAR(3) | FK currencies, NOT NULL | |
| `exchange_rate` | NUMERIC(18,6) | NOT NULL | Snapshot al momento de la compra |
| `subtotal` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Sin IVA, en moneda de la compra |
| `tax_total` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | |
| `total` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | |
| `total_base_currency` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Total convertido a PYG |
| `status` | ENUM `purchase_status` | NOT NULL, DEFAULT `'draft'` | |
| `notes` | TEXT | NULL | |
| `confirmed_at` | TIMESTAMPTZ | NULL | Cuándo pasó a `confirmed` |
| `cancelled_at` | TIMESTAMPTZ | NULL | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |
| `created_by_user_id`, `updated_by_user_id` | — | AuditUserMixin | |

**Enum `purchase_status`:** `draft`, `confirmed`, `cancelled`

**Constraints:**
- UNIQUE(`purchase_number`) → `uq_purchases_purchase_number`

**Índices:**
- `ix_purchases_supplier_id`
- `ix_purchases_purchase_date`
- `ix_purchases_status`

---

### 6.2 `purchase_items`

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `purchase_id` | UUID | FK purchases, NOT NULL, ON DELETE CASCADE | |
| `product_id` | UUID | FK products, NOT NULL | |
| `product_unit_id` | UUID | FK product_units, NOT NULL | Unidad en que se compró |
| `quantity` | NUMERIC(18,4) | NOT NULL | En unidad de compra |
| `quantity_base` | NUMERIC(18,4) | NOT NULL | Snapshot del factor × quantity |
| `unit_cost` | NUMERIC(18,4) | NOT NULL | En moneda de la compra |
| `unit_cost_base_currency` | NUMERIC(18,4) | NOT NULL | Convertido a PYG con exchange_rate |
| `tax_rate` | NUMERIC(5,2) | NOT NULL, DEFAULT 0 | Snapshot |
| `tax_included` | BOOLEAN | NOT NULL, DEFAULT TRUE | Snapshot |
| `subtotal` | NUMERIC(18,4) | NOT NULL | Sin IVA, en moneda de la compra |
| `tax_amount` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | |
| `total` | NUMERIC(18,4) | NOT NULL | Con IVA |
| `line_number` | SMALLINT | NOT NULL | Orden de aparición |

**Constraints:**
- CHECK(`quantity > 0`) → `ck_purchase_items_quantity_positive`
- CHECK(`unit_cost >= 0`) → `ck_purchase_items_cost_non_negative`

**Índices:**
- `ix_purchase_items_purchase_id`
- `ix_purchase_items_product_id`

**Flujo de confirmación (transacción atómica):**
1. Cambiar `purchases.status` de `draft` a `confirmed`, setear `confirmed_at`
2. Para cada item, generar `stock_movement` con `direction='in'`, `movement_type='purchase'`, `unit_cost_base = unit_cost_base_currency`
3. Bloquear con `SELECT FOR UPDATE` la fila de `stock_current` correspondiente
4. Recalcular CPP y actualizar `stock_current.quantity_base` y `avg_cost_base`
5. Si stock_current no existe (primera compra del producto en ese depósito), insertarlo
6. Commit. Si cualquier paso falla, rollback completo.

**Cancelación de compra confirmada:** genera movimientos compensatorios (`movement_type='return_out'` por cada item original), no borra. CPP no se recalcula hacia atrás — se considera que el costo histórico se mantiene.

---

## Módulo 7 — Ventas (POS)

### 7.1 `sales`

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `sale_number` | VARCHAR(30) | NOT NULL, UNIQUE | Correlativo interno |
| `customer_id` | UUID | FK contacts, NULL | Venta sin cliente identificado posible |
| `sale_date` | TIMESTAMPTZ | NOT NULL | Importa la hora en POS |
| `warehouse_id` | UUID | FK warehouses, NOT NULL | Depósito que descuenta |
| `currency_code` | VARCHAR(3) | FK currencies, NOT NULL | |
| `exchange_rate` | NUMERIC(18,6) | NOT NULL | Snapshot |
| `items_subtotal` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Sin IVA, sin descuentos cabecera |
| `items_discount_total` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Suma de descuentos por item |
| `header_discount_amount` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Descuento sobre el total |
| `header_discount_type` | ENUM `discount_type` | NOT NULL, DEFAULT `'amount'` | Si es `percent`, `header_discount_amount` es el valor resultante (no el %) |
| `header_discount_percent` | NUMERIC(5,2) | NULL | Guardar el % si el descuento fue por porcentaje |
| `tax_total` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | |
| `total` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Final cobrado |
| `total_base_currency` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Convertido a PYG |
| `cost_total_base` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Suma de costos para utilidad |
| `status` | ENUM `sale_status` | NOT NULL, DEFAULT `'confirmed'` | POS típicamente confirma directo |
| `notes` | TEXT | NULL | |
| `cancelled_at` | TIMESTAMPTZ | NULL | |
| `cancelled_reason` | TEXT | NULL | |
| `created_at`, `updated_at`, `deleted_at` | — | mixins | |
| `created_by_user_id`, `updated_by_user_id` | — | AuditUserMixin | |

**Enums:**
- `sale_status`: `draft`, `confirmed`, `cancelled`
- `discount_type`: `amount`, `percent`

**Constraints:**
- UNIQUE(`sale_number`) → `uq_sales_sale_number`

**Índices:**
- `ix_sales_sale_date`
- `ix_sales_customer_id`
- `ix_sales_status`
- `ix_sales_warehouse_id`

---

### 7.2 `sale_items`

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `sale_id` | UUID | FK sales, NOT NULL, ON DELETE CASCADE | |
| `product_id` | UUID | FK products, NOT NULL | |
| `product_unit_id` | UUID | FK product_units, NOT NULL | |
| `quantity` | NUMERIC(18,4) | NOT NULL | En unidad de venta |
| `quantity_base` | NUMERIC(18,4) | NOT NULL | Convertido a base_unit |
| `unit_price` | NUMERIC(18,4) | NOT NULL | En moneda de la venta |
| `discount_amount` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | Descuento sobre este item |
| `discount_type` | ENUM `discount_type` | NOT NULL, DEFAULT `'amount'` | |
| `discount_percent` | NUMERIC(5,2) | NULL | Si fue por porcentaje |
| `tax_rate` | NUMERIC(5,2) | NOT NULL, DEFAULT 0 | Snapshot |
| `tax_included` | BOOLEAN | NOT NULL, DEFAULT TRUE | Snapshot |
| `subtotal` | NUMERIC(18,4) | NOT NULL | Sin IVA, sin descuento |
| `tax_amount` | NUMERIC(18,4) | NOT NULL, DEFAULT 0 | |
| `total` | NUMERIC(18,4) | NOT NULL | Con IVA y descuento aplicado |
| `unit_cost_base_at_sale` | NUMERIC(18,4) | NOT NULL | Snapshot del `avg_cost_base` para utilidad |
| `line_number` | SMALLINT | NOT NULL | Orden de aparición |

**Constraints:**
- CHECK(`quantity > 0`) → `ck_sale_items_quantity_positive`
- CHECK(`unit_price >= 0`) → `ck_sale_items_price_non_negative`

**Índices:**
- `ix_sale_items_sale_id`
- `ix_sale_items_product_id`

**Flujo de confirmación (transacción atómica con lock pesimista):**
1. Validar que `customer_id` esté presente si `settings.sale_requires_customer = true`
2. Para cada item:
   - `SELECT ... FOR UPDATE` sobre `stock_current` del producto+depósito
   - Si `settings.allow_negative_stock = false` y `stock_current.quantity_base < quantity_base` → abortar con error
   - Calcular `unit_cost_base_at_sale = stock_current.avg_cost_base`
   - Generar `stock_movement` con `direction='out'`, `movement_type='sale'`
   - Actualizar `stock_current.quantity_base -= quantity_base` (el `avg_cost_base` no cambia en salidas)
3. Validar que la suma de `sale_payments.amount` = `sales.total`
4. Insertar `sale_items`, `sale_payments`, y `sales` con `status='confirmed'`
5. Commit

**Cancelación de venta confirmada:** genera movimientos compensatorios (`movement_type='return_in'`). El stock vuelve, pero el `avg_cost_base` no se recalcula hacia atrás (se considera la devolución al costo de venta original).

---

### 7.3 `sale_payments`

Pagos asociados a una venta. Soporta pagos mixtos (efectivo + transferencia).

| Columna | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | UUID | PK | |
| `sale_id` | UUID | FK sales, NOT NULL, ON DELETE CASCADE | |
| `payment_method` | ENUM `payment_method` | NOT NULL | |
| `amount` | NUMERIC(18,4) | NOT NULL | En moneda de la venta |
| `reference` | VARCHAR(100) | NULL | Nº transferencia, últimos 4 de tarjeta, etc. |
| `notes` | TEXT | NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**Enum `payment_method`:** `cash`, `transfer`, `card_debit`, `card_credit`, `check`, `other`

**Constraints:**
- CHECK(`amount > 0`) → `ck_sale_payments_amount_positive`

**Índices:**
- `ix_sale_payments_sale_id`

**Regla:** la suma de `sale_payments.amount` debe igualar `sales.total`. Validación en service al confirmar la venta.

---

## Diagrama de dependencias FK

```
users ←── (created_by/updated_by) ─── [casi todas las tablas]
currencies ←── exchange_rates
currencies ←── product_prices, purchases, sales

product_categories ──↑ (self)
product_categories ←── products
products ←── product_units
product_units ←── product_prices
products, product_units ←── purchase_items, sale_items, stock_movements, stock_adjustment_items
warehouses ←── stock_current, stock_movements, stock_adjustments, purchases, sales

contacts ←── purchases (supplier_id)
contacts ←── sales (customer_id)

purchases ←── purchase_items
sales ←── sale_items, sale_payments
stock_adjustments ←── stock_adjustment_items

products + warehouses ←── stock_current (PK compuesta)
```

---

## Orden de creación en Alembic (migración inicial)

1. Enums (`user_role`, `setting_value_type`, etc.)
2. `users`, `settings`, `currencies`, `warehouses`, `product_categories`
3. `exchange_rates`, `contacts`, `products`
4. `product_units`, `product_prices`
5. `stock_current`
6. `stock_movements`
7. `purchases`, `purchase_items`
8. `sales`, `sale_items`, `sale_payments`
9. `stock_adjustments`, `stock_adjustment_items`
10. `audit_log` (último, sin FKs salvo a `users`)

---

## Tablas que se difieren a versiones futuras

**v2 sugeridas:**
- `cash_registers` + `cash_register_shifts` + `cash_movements` — caja/turnos/arqueo
- `credit_notes` + `credit_note_items` — formalizar devoluciones como documento
- `price_lists` + `price_list_items` — listas de precios diferenciadas (mayorista/minorista)
- UI de `warehouses` (multi-depósito real)
- Roles y permisos granulares

**v3 sugeridas:**
- Integración SET (facturación electrónica): timbrado, punto de expedición, número de comprobante, CDC, QR
- Cuentas corrientes de clientes/proveedores
- Lotes y vencimientos por producto
