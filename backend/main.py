from dotenv import load_dotenv
load_dotenv()

import logging
import os
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.contacts import router as contacts_router
from app.api.prices import router as prices_router, router_standalone as prices_standalone_router
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
from app.exceptions import DTCoreError
from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="DTCore API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers globales
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        content = {"detail": exc.detail}
    else:
        content = {"detail": {"code": "http_error", "message": str(exc.detail)}}
    headers = getattr(exc, "headers", None)
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.exception_handler(DTCoreError)
async def dtcore_error_handler(request: Request, exc: DTCoreError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "validation_error",
                "message": "Datos de entrada inválidos",
                "errors": errors,
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.exception("IntegrityError en %s %s", request.method, request.url.path)
    orig = exc.orig
    constraint = getattr(getattr(orig, "diag", None), "constraint_name", None)
    detail_str = str(orig) if orig else str(exc)

    if constraint == "uq_product_prices_unit_currency_date" or (
        "uq_product_prices_unit_currency_date" in detail_str
    ):
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "duplicate_price_date",
                    "message": (
                        "Ya existe un precio para esta unidad y moneda con esa fecha de vigencia. "
                        "Eliminá el existente o cargá con otra fecha."
                    ),
                    "constraint": "uq_product_prices_unit_currency_date",
                }
            },
        )

    if "unique" in detail_str.lower() or (constraint and "uq_" in constraint):
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "duplicate_value",
                    "message": "Ya existe un registro con esos valores",
                    "constraint": constraint or "unknown",
                }
            },
        )

    return JSONResponse(
        status_code=409,
        content={
            "detail": {
                "code": "integrity_error",
                "message": "Conflicto de integridad en la base de datos",
                "constraint": constraint or "unknown",
            }
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Error inesperado en %s %s\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "internal_error", "message": "Error interno del servidor"}},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(categories_router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(contacts_router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(products_router, prefix="/api/v1/products", tags=["products"])
app.include_router(product_units_router, prefix="/api/v1/products", tags=["product-units"])
app.include_router(prices_router, prefix="/api/v1/products", tags=["prices"])
app.include_router(prices_standalone_router, prefix="/api/v1/prices", tags=["prices"])
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


@app.on_event("startup")
async def on_startup() -> None:
    env = os.getenv("ENVIRONMENT", "development")
    logger.info("DTCore API v%s iniciando en entorno: %s", app.version, env)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("DTCore API detenida (graceful shutdown)")
