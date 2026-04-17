from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


LOW_STOCK_THRESHOLD = 5

CUSTOM_FIELDS_MAX_KEYS = 50
CUSTOM_FIELD_KEY_MAX_LENGTH = 64
CUSTOM_FIELD_VALUE_MAX_LENGTH = 500


class _Missing:
    """Sentinel for payload fields that were omitted vs. explicitly null."""

    _instance: Optional["_Missing"] = None

    def __new__(cls) -> "_Missing":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "MISSING"


MISSING = _Missing()


def _read_required_text(payload: Mapping[str, Any], key: str, label: str, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")

    text = value.strip()
    if len(text) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer.")
    return text


def _read_optional_text(payload: Mapping[str, Any], key: str, label: str, max_length: int) -> Optional[str]:
    if key not in payload:
        return None

    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")

    text = value.strip()
    if len(text) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer.")
    return text


def _read_required_int(payload: Mapping[str, Any], key: str, label: str) -> int:
    try:
        value = int(payload.get(key, 0))
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an integer.") from None

    if value < 0:
        raise ValueError(f"{label} must be 0 or greater.")
    return value


def _read_optional_int(payload: Mapping[str, Any], key: str, label: str) -> Optional[int]:
    if key not in payload:
        return None

    value = payload.get(key)
    if value is None:
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an integer.") from None

    if parsed < 0:
        raise ValueError(f"{label} must be 0 or greater.")
    return parsed


def _read_threshold_for_create(payload: Mapping[str, Any], label: str) -> Optional[int]:
    """Create-time threshold: absent or null both mean 'use default'."""
    if "low_stock_threshold" not in payload:
        return None
    value = payload.get("low_stock_threshold")
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an integer.") from None
    if parsed < 1:
        raise ValueError(f"{label} must be 1 or greater.")
    return parsed


def _read_threshold_for_update(payload: Mapping[str, Any], label: str):
    """Update-time threshold: distinguish absent (MISSING) vs null (clear) vs int."""
    if "low_stock_threshold" not in payload:
        return MISSING
    value = payload.get("low_stock_threshold")
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an integer.") from None
    if parsed < 1:
        raise ValueError(f"{label} must be 1 or greater.")
    return parsed


def _validate_custom_fields(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Custom fields must be a JSON object.")
    if len(value) > CUSTOM_FIELDS_MAX_KEYS:
        raise ValueError(f"At most {CUSTOM_FIELDS_MAX_KEYS} custom fields are allowed.")

    cleaned: Dict[str, Any] = {}
    for raw_key, raw_val in value.items():
        if not isinstance(raw_key, str):
            raise ValueError("Custom field keys must be strings.")
        key = raw_key.strip()
        if not key:
            raise ValueError("Custom field keys must not be empty.")
        if len(key) > CUSTOM_FIELD_KEY_MAX_LENGTH:
            raise ValueError(
                f"Custom field key must be {CUSTOM_FIELD_KEY_MAX_LENGTH} characters or fewer."
            )
        if key in cleaned:
            raise ValueError(f"Duplicate custom field key: {key!r}.")

        if raw_val is None or isinstance(raw_val, bool) or isinstance(raw_val, (int, float)):
            cleaned[key] = raw_val
        elif isinstance(raw_val, str):
            if len(raw_val) > CUSTOM_FIELD_VALUE_MAX_LENGTH:
                raise ValueError(
                    f"Custom field {key!r} must be {CUSTOM_FIELD_VALUE_MAX_LENGTH} characters or fewer."
                )
            cleaned[key] = raw_val
        else:
            raise ValueError(
                f"Custom field {key!r} must be a string, number, boolean, or null."
            )
    return cleaned


def _read_custom_fields_for_create(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if "custom_fields" not in payload:
        return {}
    value = payload.get("custom_fields")
    if value is None:
        return {}
    return _validate_custom_fields(value)


def _read_custom_fields_for_update(payload: Mapping[str, Any]):
    if "custom_fields" not in payload:
        return MISSING
    value = payload.get("custom_fields")
    if value is None:
        return {}
    return _validate_custom_fields(value)


@dataclass
class Product:
    id: int
    sku: str
    name: str
    stock_qty: int
    low_stock_threshold: Optional[int] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def effective_threshold(self) -> int:
        if self.low_stock_threshold is None:
            return LOW_STOCK_THRESHOLD
        return self.low_stock_threshold

    @property
    def status(self) -> str:
        if self.stock_qty <= 0:
            return "out"
        if self.stock_qty < self.effective_threshold:
            return "low"
        return "ok"

    @property
    def needs_restock(self) -> bool:
        return 0 < self.stock_qty < self.effective_threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "stock_qty": self.stock_qty,
            "status": self.status,
            "needs_restock": self.needs_restock,
            "low_stock_threshold": self.low_stock_threshold,
            "restock_threshold": self.effective_threshold,
            "default_restock_threshold": LOW_STOCK_THRESHOLD,
            "custom_fields": self.custom_fields,
        }


@dataclass
class ProductCreate:
    sku: str
    name: str
    stock_qty: int = 0
    low_stock_threshold: Optional[int] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProductCreate":
        return cls(
            sku=_read_required_text(payload, "sku", "SKU", 64),
            name=_read_required_text(payload, "name", "Product name", 200),
            stock_qty=_read_required_int(payload, "stock_qty", "Stock quantity"),
            low_stock_threshold=_read_threshold_for_create(payload, "Low stock threshold"),
            custom_fields=_read_custom_fields_for_create(payload),
        )


@dataclass
class ProductUpdate:
    sku: Optional[str] = None
    name: Optional[str] = None
    stock_qty: Optional[int] = None
    low_stock_threshold: Any = MISSING
    custom_fields: Any = MISSING

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProductUpdate":
        update = cls(
            sku=_read_optional_text(payload, "sku", "SKU", 64),
            name=_read_optional_text(payload, "name", "Product name", 200),
            stock_qty=_read_optional_int(payload, "stock_qty", "Stock quantity"),
            low_stock_threshold=_read_threshold_for_update(payload, "Low stock threshold"),
            custom_fields=_read_custom_fields_for_update(payload),
        )
        if (
            update.sku is None
            and update.name is None
            and update.stock_qty is None
            and update.low_stock_threshold is MISSING
            and update.custom_fields is MISSING
        ):
            raise ValueError("At least one field is required for update.")
        return update


USERNAME_MAX_LENGTH = 64
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 128


def _read_required_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


@dataclass
class User:
    id: int
    username: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "username": self.username}


@dataclass
class LoginRequest:
    username: str
    password: str
    remember: bool = False

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "LoginRequest":
        username = payload.get("username")
        password = payload.get("password")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Username is required.")
        if not isinstance(password, str) or not password:
            raise ValueError("Password is required.")
        username = username.strip()
        if len(username) > USERNAME_MAX_LENGTH:
            raise ValueError(f"Username must be {USERNAME_MAX_LENGTH} characters or fewer.")
        if len(password) > PASSWORD_MAX_LENGTH:
            raise ValueError(f"Password must be {PASSWORD_MAX_LENGTH} characters or fewer.")
        return cls(
            username=username,
            password=password,
            remember=_read_required_bool(payload, "remember"),
        )


@dataclass
class DeleteConfirmation:
    password: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DeleteConfirmation":
        password = payload.get("password")
        if not isinstance(password, str) or not password:
            raise ValueError("Password is required to confirm deletion.")
        return cls(password=password)
