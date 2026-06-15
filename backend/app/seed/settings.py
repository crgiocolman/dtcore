import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.enums import SettingValueType
from app.models.settings import Setting
from app.seed.warehouses import MAIN_WAREHOUSE_ID

logger = logging.getLogger(__name__)

_SETTINGS = [
    {
        "key": "business_name",
        "value": "Rincón de Embalajes",
        "value_type": SettingValueType.STRING,
        "description": "Nombre del negocio mostrado en la interfaz",
    },
    {
        "key": "business_document",
        "value": "",
        "value_type": SettingValueType.STRING,
        "description": "RUC o documento del negocio",
    },
    {
        "key": "default_currency_code",
        "value": "PYG",
        "value_type": SettingValueType.STRING,
        "description": "Moneda base del sistema (ISO 4217)",
    },
    {
        "key": "allow_negative_stock",
        "value": "false",
        "value_type": SettingValueType.BOOL,
        "description": "Permite confirmar ventas aunque el stock quede negativo",
    },
    {
        "key": "default_warehouse_id",
        "value": str(MAIN_WAREHOUSE_ID),
        "value_type": SettingValueType.STRING,
        "description": "UUID del depósito seleccionado por defecto en el POS",
    },
    {
        "key": "low_stock_default_threshold",
        "value": "5",
        "value_type": SettingValueType.DECIMAL,
        "description": "Umbral de stock bajo por defecto para productos sin override",
    },
    {
        "key": "sale_requires_customer",
        "value": "false",
        "value_type": SettingValueType.BOOL,
        "description": "Si true, el POS exige seleccionar un cliente antes de confirmar",
    },
    {
        "key": "default_tax_rate",
        "value": "10",
        "value_type": SettingValueType.DECIMAL,
        "description": "Tasa de IVA por defecto al crear nuevos productos (0, 5 o 10)",
    },
    {
        "key": "business_timezone",
        "value": "America/Asuncion",
        "value_type": SettingValueType.STRING,
        "description": "Zona horaria del negocio. Usado para clasificar fechas en cálculos diarios y reportes.",
    },
]


async def seed_settings() -> None:
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(Setting).values(_SETTINGS).on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()
    logger.info("seed_settings: %d settings procesadas", len(_SETTINGS))
