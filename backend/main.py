from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.contacts import router as contacts_router
from app.api.prices import router as prices_router
from app.api.product_units import router as product_units_router
from app.api.products import router as products_router
from app.api.currencies import router as currencies_router
from app.api.exchange_rates import router as exchange_rates_router
from app.api.settings import router as settings_router
from app.api.adjustments import router as adjustments_router
from app.api.reports import router as reports_router
from app.api.purchases import router as purchases_router
from app.api.sales import router as sales_router
from app.api.stock import router as stock_router
from app.api.unit_catalog import router as unit_catalog_router
from app.api.warehouses import router as warehouses_router

app = FastAPI(title="DTCore API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(categories_router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(contacts_router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(products_router, prefix="/api/v1/products", tags=["products"])
app.include_router(product_units_router, prefix="/api/v1/products", tags=["product-units"])
app.include_router(prices_router, prefix="/api/v1/products", tags=["prices"])
app.include_router(currencies_router, prefix="/api/v1/currencies", tags=["currencies"])
app.include_router(exchange_rates_router, prefix="/api/v1/exchange-rates", tags=["exchange-rates"])
app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(adjustments_router, prefix="/api/v1/adjustments", tags=["adjustments"])
app.include_router(reports_router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(purchases_router, prefix="/api/v1/purchases", tags=["purchases"])
app.include_router(sales_router, prefix="/api/v1/sales", tags=["sales"])
app.include_router(stock_router, prefix="/api/v1/stock", tags=["stock"])
app.include_router(unit_catalog_router, prefix="/api/v1/units", tags=["unit-catalog"])
app.include_router(warehouses_router, prefix="/api/v1/warehouses", tags=["warehouses"])
