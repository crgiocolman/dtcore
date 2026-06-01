# docs/common-patterns.md — Patrones de código del proyecto DTCore

Patrones recurrentes en el código. Referencia para Claude Code cuando replica un patrón existente. Este archivo se llena **reactivamente** a medida que aparecen patrones en código real, no a priori.

Los patrones iniciales abajo vienen del diseño y de TributarioPY (adaptados). Los demás se agregarán durante la ejecución.

---

## Enums Python + PostgreSQL nativos

```python
# app/enums.py
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"

class StockMovementType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    INITIAL = "initial"
```

En el modelo SQLAlchemy:

```python
from sqlalchemy import Enum as SQLEnum

movement_type = Column(
    SQLEnum(
        StockMovementType,
        name="stock_movement_type",
        native_enum=True,
        create_type=True,
        values_callable=lambda obj: [e.value for e in obj],
    ),
    nullable=False,
)
```

---

## FK con nombre explícito

```python
supplier_id = Column(
    UUID(as_uuid=True),
    ForeignKey("contacts.id", ondelete="RESTRICT", name="fk_purchases_supplier_id"),
    nullable=False,
)
```

Convenciones:
- FK: `fk_<tabla>_<columna>`
- Unique: `uq_<tabla>_<columna>` o `uq_<tabla>_<col1>_<col2>`
- Índice: `ix_<tabla>_<columna>`
- Check: `ck_<tabla>_<descripcion>`

---

## Timestamps con timezone

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)  # Correcto
# datetime.utcnow()  # MAL — deprecated
```

SQLAlchemy:
```python
created_at = Column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
)
```

---

## Montos NUMERIC(18,4)

```python
from sqlalchemy import Numeric

unit_price = Column(Numeric(18, 4), nullable=False, default=0)
exchange_rate = Column(Numeric(18, 6), nullable=False)  # Tipos de cambio con más precisión
```

Nunca `Float` ni `BigInteger` para montos. Redondeo a la presentación según `currencies.decimal_places`.

---

## Mixins para campos comunes

```python
# app/models/mixins.py
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class AuditUserMixin:
    @declared_attr
    def created_by_user_id(cls):
        return Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    @declared_attr
    def updated_by_user_id(cls):
        return Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
```

---

## Settings con pydantic-settings

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRES_HOURS: int = 8
    STORAGE_PATH: str = "./storage"

settings = Settings()
```

---

## Lock pesimista para actualización de stock

Patrón obligatorio en toda función que modifique `stock_current`:

```python
async def apply_stock_movement(
    db: AsyncSession,
    product_id: UUID,
    warehouse_id: UUID,
    quantity_base: Decimal,
    direction: StockDirection,
    movement_type: StockMovementType,
    unit_cost_base: Decimal | None = None,
    reference_type: StockReferenceType | None = None,
    reference_id: UUID | None = None,
    user_id: UUID | None = None,
) -> StockMovement:
    # 1. Lock pesimista sobre stock_current
    stmt = (
        select(StockCurrent)
        .where(
            StockCurrent.product_id == product_id,
            StockCurrent.warehouse_id == warehouse_id,
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    current = result.scalar_one_or_none()

    # 2. Si no existe, crearlo (primera vez para este producto+depósito)
    if current is None:
        current = StockCurrent(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_base=Decimal(0),
            avg_cost_base=Decimal(0),
        )
        db.add(current)
        await db.flush()

    # 3. Validar stock disponible si es salida y no se permite negativo
    if direction == StockDirection.OUT:
        allow_negative = await settings_service.get_setting(db, "allow_negative_stock")
        if not allow_negative and current.quantity_base < quantity_base:
            raise InsufficientStockError(product_id, current.quantity_base, quantity_base)

    # 4. Insertar el movement (ledger append-only)
    movement = StockMovement(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        direction=direction,
        quantity_base=quantity_base,
        unit_cost_base=unit_cost_base,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by_user_id=user_id,
    )
    db.add(movement)

    # 5. Actualizar stock_current
    if direction == StockDirection.IN:
        # Recalcular CPP
        if current.quantity_base + quantity_base > 0:
            current.avg_cost_base = (
                (current.quantity_base * current.avg_cost_base + quantity_base * unit_cost_base)
                / (current.quantity_base + quantity_base)
            )
        current.quantity_base += quantity_base
    else:
        current.quantity_base -= quantity_base

    current.last_movement_at = datetime.now(timezone.utc)
    await db.flush()
    return movement
```

**Importante:** esta función NUNCA hace commit por sí misma. El commit lo hace la transacción exterior (confirm_purchase, confirm_sale, etc.).

---

## Transacción atómica con rollback explícito en services

```python
async def confirm_purchase(db: AsyncSession, purchase_id: UUID, user_id: UUID) -> Purchase:
    try:
        purchase = await get_purchase_or_404(db, purchase_id)
        if purchase.status != PurchaseStatus.DRAFT:
            raise InvalidStateError("Solo se pueden confirmar compras en estado draft")

        # Cambiar estado
        purchase.status = PurchaseStatus.CONFIRMED
        purchase.confirmed_at = datetime.now(timezone.utc)
        purchase.updated_by_user_id = user_id

        # Generar movimientos de stock por cada item
        for item in purchase.items:
            await apply_stock_movement(
                db=db,
                product_id=item.product_id,
                warehouse_id=purchase.warehouse_id,
                quantity_base=item.quantity_base,
                direction=StockDirection.IN,
                movement_type=StockMovementType.PURCHASE,
                unit_cost_base=item.unit_cost_base_currency,
                reference_type=StockReferenceType.PURCHASE,
                reference_id=purchase.id,
                user_id=user_id,
            )

        await db.commit()
        return purchase

    except Exception as e:
        await db.rollback()
        logger.exception("Error confirmando compra %s: %s", purchase_id, e)
        raise
```

---

## Layout de páginas con formulario largo (React + Tailwind)

Las páginas con formularios largos necesitan **nested scroll container** para evitar fondo blanco bajo el contenido.

### Estructura correcta

```tsx
<div className="flex flex-col h-full">       {/* ocupa altura de <main> */}
  <div className="flex items-center ...">     {/* header fijo arriba */}
    ...
  </div>
  <form className="flex-1 overflow-y-auto">   {/* scroll propio del form */}
    ...
  </form>
</div>
```

**Por qué funciona:** `h-full` llena `main` (que tiene `flex-1` en AppLayout). El form tiene `flex-1 overflow-y-auto`, así que scrollea internamente. El body nunca scrollea.

### Qué NO hacer

```tsx
{/* MAL: el body scrollea y aparece fondo blanco */}
<div className="min-h-full">
  <div className="sticky top-0">...</div>
  <form>...</form>
</div>
```

---

## `<input type="file">` oculto dentro de `<label>`

Para reemplazar el input de archivo nativo con un botón custom, usar `hidden` (no `sr-only`).

```tsx
{/* CORRECTO */}
<label className="cursor-pointer">
  <input type="file" className="hidden" onChange={...} />
  <div className="...">Elegir archivo</div>
</label>
```

`sr-only` usa `position: absolute` sin contenedor posicionado → el input se ubica relativo al viewport → extiende el body → fondo blanco en forms largos. `hidden` (`display: none`) lo saca del layout completamente; el label igual abre el file picker.

---

## Sistema visual

### Filosofía
Dark mode profundo como default en v1. Fondos azulados (no grises). Tokens semánticos via CSS variables en `index.css` → habilitar light mode en v2 reemplazando solo `:root` sin tocar componentes. Tipografía Inter.

### Cuándo usar cada botón

| Clase | Cuándo |
|---|---|
| `.btn-primary` | Acciones generales: Guardar, Confirmar, Agregar |
| `.btn-accent` | **SOLO** la acción de Cobrar en el POS. Un único `.btn-accent` por pantalla. |
| `.btn-secondary` | Acciones secundarias: Cancelar, Volver, Ver detalle |
| `.btn-danger` | Acciones destructivas: Eliminar, Cancelar venta/compra |
| `.btn-ghost` | Iconos en barras de herramientas, acciones muy sutiles |

### Cuándo usar cada color semántico

| Color | Cuándo |
|---|---|
| `success-*` | Confirmaciones de operación exitosa, indicador de stock OK |
| `warning-*` | Stock bajo, advertencias no críticas, alertas informativas |
| `danger-*` | Errores de validación, acciones destructivas, stock agotado |
| `info-*` / `accent-*` | Información neutral, destacar sin alarmar |

### Tokens de fondo — nunca usar `bg-white`, `bg-gray-*`, `bg-slate-*`

| Token | Uso |
|---|---|
| `bg-bg-base` | Fondo de página (más oscuro, el "suelo") |
| `bg-bg-surface` | Cards, sidebar, header, modales |
| `bg-bg-elevated` | Dropdowns, tooltips, hover sobre surface |
| `bg-bg-input` | Campos de formulario (`.input` lo aplica automático) |

### Tokens de texto — nunca usar `text-white`, `text-gray-*`, `text-slate-*`

| Token | Uso |
|---|---|
| `text-text-primary` | Texto principal, títulos, contenido importante |
| `text-text-secondary` | Labels de formulario, texto secundario |
| `text-text-muted` | Placeholders, metadatos, texto de ayuda |

### Tokens de borde

| Token | Uso |
|---|---|
| `border-border-subtle` | Divisores internos, sidebar, header |
| `border-border` | Inputs, cards, separadores con más peso |
| `border-border-focus` | Anillo de foco activo (`.input` lo aplica automático) |

### Números tabulares
En tablas de montos, precios o cantidades: clase `tabular-nums` en el contenedor, o `td.numeric` en celdas individuales. El `.input` de tipo `number` ya aplica `font-variant-numeric: tabular-nums` automáticamente.

---

## Toggle activo/inactivo vs eliminar (product_units)

Cuándo aplicar cada acción en la UI de unidades:

| Situación | Acción disponible |
|---|---|
| Unidad sin referencias (nunca usada) | Toggle activo/inactivo + Trash (hard delete) |
| Unidad con referencias (compras, ventas, precios) | Solo toggle activo/inactivo |
| Unidad base (factor_to_base = 1) | Solo editar (no toggle, no eliminar) |

**Backend:** `can_hard_delete: bool` se devuelve por unidad en `GET /products/{id}/units`. El frontend muestra el ícono Trash solo cuando es `true`.

**Toggle activo:** endpoint `PATCH /products/{id}/units/{unit_id}/toggle-active`. Si la unidad desactivada era default de venta/compra, el backend reasigna esos flags a la unidad base automáticamente.

**Conflicto al crear unidad con nombre existente inactiva:** el backend devuelve 409 con `{"code": "exists_inactive", "unit_id": "..."}`. El frontend detecta ese `code` y muestra el modal "¿Querés reactivarla?" en lugar del error genérico.

```typescript
// Detectar error estructurado en el frontend
const structured = parseApiErrorStructured(err)
if (structured.code === 'exists_inactive' && structured.unit_id) {
  setReactivateModal({ unitName: data.unit_name, conflictingUnitId: structured.unit_id })
} else {
  setUnitError(structured.message)
}
```

---

## Cómo agregar nuevos patrones

Cuando un patrón aparece 2+ veces en código, documentarlo acá. Formato:

```
## [Nombre del patrón]

[1-2 líneas de cuándo aplica]

\`\`\`[lenguaje]
[ejemplo de código]
\`\`\`

[Por qué funciona / qué evita — opcional]
```

---

## JSON serialization para JSONB

Cualquier columna `JSONB` en el sistema (ej. `audit_log.changes`) hereda automáticamente el serializer custom definido en `app/database.py`. El engine se crea con `json_serializer=_json_serializer`, que maneja:

- `UUID` → `str(uuid)` (ej. `"550e8400-e29b-41d4-a716-446655440000"`)
- `datetime` / `date` → `obj.isoformat()`
- `Decimal` → `str(decimal)`

No hay que hacer nada especial en los services: pasá el dict directamente y el engine lo serializa al escribir a Postgres.

```python
# Correcto — el engine serializa el UUID automáticamente
changes = {"base_unit_id": {"old": old_uuid, "new": new_uuid}}  # old_uuid: UUID
record.changes = changes  # columna JSONB

# Incorrecto — no hagas esto manualmente
changes = {"base_unit_id": {"old": str(old_uuid), "new": str(new_uuid)}}
```

Si en el futuro se agrega un tipo nuevo que falle, extender `_json_default` en `app/database.py` (un solo lugar).

---

## Helpers de formateo numérico (`src/lib/format.ts`)

Funciones para mostrar cantidades y tipos de cambio respetando las convenciones locales (es-PY: punto como separador de miles, coma como decimal).

```typescript
import { formatQuantity, formatExchangeRate } from '../../../lib/format'

// Cantidad según tipo de unidad
formatQuantity('3', 'count')    // "3"      — sin decimales
formatQuantity('3.5', 'weight') // "3,5"    — hasta 3 decimales, sin trailing zeros
formatQuantity('3.500', 'weight') // "3,5"  — trailing zeros eliminados

// Tipo de cambio
formatExchangeRate('7400')      // "7.400"  — sin parte decimal → entero con separador de miles
formatExchangeRate('7400.50')   // "7.400,50" — con decimales → hasta 2
```

**Regla:** el backend siempre guarda `NUMERIC(18,4)` / `NUMERIC(18,6)` con precisión completa. Los helpers solo afectan la presentación.

**Cuándo usar cada uno:**
- `formatQuantity`: cualquier columna o campo que muestre una cantidad de stock o de ítem
- `formatExchangeRate`: campo TC en cabecera de compra/venta (editable e read-only)

---

## Atajos de teclado en formularios de ítems (`useItemFormShortcuts`)

Hook para agregar ítems con teclado sin usar el mouse. Pensado para compras, ventas y POS.

```typescript
// src/features/purchases/hooks/useItemFormShortcuts.ts
import { useItemFormShortcuts } from '../hooks/useItemFormShortcuts'

const { onKeyDown: onItemInputKeyDown } = useItemFormShortcuts(handleAddItem, clearItemForm)

// Aplicar en inputs type="text" y type="number" (NO en <select>)
<input ... onKeyDown={onItemInputKeyDown} />
```

**Comportamiento:**
- `Enter` en cualquier input text/number del formulario → llama `onAdd` (equivalente a click en "Agregar ítem")
- `Escape` → llama `onClear` (limpia el formulario, devuelve foco al campo de producto)

**Por qué no en `<select>`:** `Enter` en un `<select>` tiene comportamiento nativo del browser (cierra el dropdown). Capturarlo rompería la navegación con teclado.

**Nota de implementación:** el hook no usa React hooks internos (sin `useState`/`useEffect`). Es una función que retorna un event handler. Debe llamarse después de que `onAdd` y `onClear` estén definidos como `const` en el componente.

---

Patrones que no han aparecido todavía pero se esperan:
- Estructura de service con `get_or_404`, `create`, `update`, `delete`
- Estructura de router con dependencias de auth y db
- Hook custom de fetch con manejo de loading/error
- Componente de búsqueda con autocomplete (para POS y selectores)
- Modal con foco gestionado y cierre con Esc
- Toast/notificación de éxito/error
- Manejo de errores de red en frontend
- Paginación cliente vs server-side
