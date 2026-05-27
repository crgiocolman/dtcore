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
