from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


class SettingValueType(str, Enum):
    STRING = "string"
    INT = "int"
    DECIMAL = "decimal"
    BOOL = "bool"
    JSON = "json"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    CONFIRM = "confirm"
    CANCEL = "cancel"


class ContactType(str, Enum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


class DocumentType(str, Enum):
    RUC = "ruc"
    CI = "ci"
    PASSPORT = "passport"
    NONE = "none"


class StockMovementType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    INITIAL = "initial"


class StockDirection(str, Enum):
    IN = "in"
    OUT = "out"


class StockReferenceType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"


class AdjustmentReason(str, Enum):
    INVENTORY_COUNT = "inventory_count"
    DAMAGE = "damage"
    LOSS = "loss"
    EXPIRED = "expired"
    CORRECTION = "correction"
    OTHER = "other"


class AdjustmentStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PurchaseStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class SaleStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class DiscountType(str, Enum):
    AMOUNT = "amount"
    PERCENT = "percent"


class PaymentMethod(str, Enum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD_DEBIT = "card_debit"
    CARD_CREDIT = "card_credit"
    CHECK = "check"
    OTHER = "other"


class UnitType(str, Enum):
    WEIGHT = "weight"
    LENGTH = "length"
    VOLUME = "volume"
    COUNT = "count"
    PACKAGE = "package"
