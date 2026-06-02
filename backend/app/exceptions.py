from __future__ import annotations

from decimal import Decimal
from uuid import UUID


class DTCoreError(Exception):
    """Base para todas las excepciones de negocio de DTCore."""

    status_code: int = 500

    def to_response(self) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 404 Not Found
# ---------------------------------------------------------------------------


class ResourceNotFoundError(DTCoreError):
    status_code = 404

    def __init__(self, entity: str, id: str | UUID | None = None) -> None:
        self.entity = entity
        self.entity_id = str(id) if id is not None else None
        super().__init__(f"{entity} no encontrado")

    def to_response(self) -> dict:
        detail: dict = {"code": "not_found", "message": f"{self.entity} no encontrado"}
        if self.entity_id:
            detail["id"] = self.entity_id
        return {"detail": detail}


# ---------------------------------------------------------------------------
# 409 Conflict
# ---------------------------------------------------------------------------


class DuplicateError(DTCoreError):
    status_code = 409

    def __init__(self, entity: str, field: str, value: str) -> None:
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(f"{entity}: {field} '{value}' ya existe")

    def to_response(self) -> dict:
        return {
            "detail": {
                "code": f"duplicate_{self.field}",
                "message": f"Ya existe un {self.entity} con {self.field} '{self.value}'",
                "field": self.field,
                "value": self.value,
            }
        }


class ConflictError(DTCoreError):
    status_code = 409

    def __init__(self, code: str, message: str, **details: object) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_response(self) -> dict:
        return {"detail": {"code": self.code, "message": self.message, **self.details}}


class InvalidStateError(DTCoreError):
    status_code = 409

    def __init__(self, entity: str, current_state: str, attempted_action: str) -> None:
        self.entity = entity
        self.current_state = current_state
        self.attempted_action = attempted_action
        super().__init__(
            f"{entity} en estado '{current_state}': '{attempted_action}' no permitido"
        )

    def to_response(self) -> dict:
        return {
            "detail": {
                "code": "invalid_state",
                "message": (
                    f"La operación '{self.attempted_action}' no está permitida "
                    f"en estado '{self.current_state}'"
                ),
                "current_state": self.current_state,
                "attempted_action": self.attempted_action,
            }
        }


# ---------------------------------------------------------------------------
# 422 Business Rule
# ---------------------------------------------------------------------------


class BusinessRuleError(DTCoreError):
    status_code = 422

    def __init__(self, code: str, message: str, **details: object) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_response(self) -> dict:
        return {"detail": {"code": self.code, "message": self.message, **self.details}}


class InsufficientStockError(BusinessRuleError):
    """Hereda de BusinessRuleError para compatibilidad con el handler global."""

    def __init__(
        self,
        product_id: UUID,
        available: Decimal,
        requested: Decimal,
        product_name: str | None = None,
    ) -> None:
        self.product_id = product_id
        self.available = available
        self.requested = requested
        self.product_name = product_name
        super().__init__(
            code="insufficient_stock",
            message=(
                f"Stock insuficiente para "
                f"{product_name or str(product_id)}: "
                f"disponible {available}, solicitado {requested}"
            ),
            product_id=str(product_id),
            product_name=product_name,
            available=str(available),
            requested=str(requested),
        )


# ---------------------------------------------------------------------------
# 403 Forbidden
# ---------------------------------------------------------------------------


class ForbiddenError(DTCoreError):
    status_code = 403

    def __init__(self, reason: str = "Permisos insuficientes") -> None:
        self.reason = reason
        super().__init__(reason)

    def to_response(self) -> dict:
        return {"detail": {"code": "forbidden", "message": self.reason}}
