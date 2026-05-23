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

Patrones que no han aparecido todavía pero se esperan:
- Estructura de service con `get_or_404`, `create`, `update`, `delete`
- Estructura de router con dependencias de auth y db
- Hook custom de fetch con manejo de loading/error
- Componente de búsqueda con autocomplete (para POS y selectores)
- Modal con foco gestionado y cierre con Esc
- Toast/notificación de éxito/error
- Manejo de errores de red en frontend
- Paginación cliente vs server-side
