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
    user_id: Optional[int] = None

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
    low_stock_threshold: Any = MISSING
    custom_fields: Any = MISSING

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProductUpdate":
        if "stock_qty" in payload:
            raise ValueError(
                "Stock quantity cannot be edited directly. "
                "Use POST /api/products/<id>/movements to receive, remove, or adjust stock."
            )
        update = cls(
            sku=_read_optional_text(payload, "sku", "SKU", 64),
            name=_read_optional_text(payload, "name", "Product name", 200),
            low_stock_threshold=_read_threshold_for_update(payload, "Low stock threshold"),
            custom_fields=_read_custom_fields_for_update(payload),
        )
        if (
            update.sku is None
            and update.name is None
            and update.low_stock_threshold is MISSING
            and update.custom_fields is MISSING
        ):
            raise ValueError("At least one field is required for update.")
        return update


# ---------------------------------------------------------------------------
# Stock movements
# ---------------------------------------------------------------------------

MOVEMENT_TYPES = ("receive", "remove", "return", "damaged", "adjust")
MOVEMENT_NOTE_MAX_LENGTH = 500


@dataclass
class StockMovement:
    id: int
    product_id: int
    user_id: int
    movement_type: str
    quantity_delta: int
    quantity_after: int
    note: Optional[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "movement_type": self.movement_type,
            "quantity_delta": self.quantity_delta,
            "quantity_after": self.quantity_after,
            "note": self.note,
            "created_at": self.created_at,
        }


@dataclass
class MovementRequest:
    """POST body for /api/products/<id>/movements.

    For `receive`/`return`/`remove`/`damaged`: `quantity` is the magnitude moved
    (must be ≥ 1). For `adjust`: `quantity` is the new absolute stock level
    (must be ≥ 0); the service computes the delta against the current value.
    """

    movement_type: str
    quantity: int
    note: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MovementRequest":
        raw_type = payload.get("type")
        if raw_type is None:
            raw_type = payload.get("movement_type")
        if not isinstance(raw_type, str) or raw_type.strip() not in MOVEMENT_TYPES:
            raise ValueError(
                f"Movement type must be one of: {', '.join(MOVEMENT_TYPES)}."
            )
        movement_type = raw_type.strip()

        if "quantity" not in payload:
            raise ValueError("Quantity is required.")
        try:
            quantity = int(payload["quantity"])
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer.") from None

        if movement_type == "adjust":
            if quantity < 0:
                raise ValueError("Quantity must be 0 or greater for an adjustment.")
        else:
            if quantity <= 0:
                raise ValueError("Quantity must be 1 or greater.")

        note = _read_optional_text(payload, "note", "Note", MOVEMENT_NOTE_MAX_LENGTH)
        return cls(movement_type=movement_type, quantity=quantity, note=note)


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 64
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 128

# Top common passwords (truncated). Reject these regardless of length to avoid
# the most predictable choices. The list intentionally stays short — for a real
# deployment, swap this for a zxcvbn-style strength estimator.
COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "passw0rd",
        "p@ssw0rd",
        "qwerty",
        "qwerty123",
        "111111",
        "123123",
        "123456",
        "1234567",
        "12345678",
        "123456789",
        "1234567890",
        "abc123",
        "abcd1234",
        "iloveyou",
        "letmein",
        "welcome",
        "welcome1",
        "admin",
        "admin1",
        "admin123",
        "administrator",
        "root",
        "toor",
        "monkey",
        "dragon",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "master",
        "shadow",
        "trustno1",
        "changeme",
        "default",
    }
)


def _read_required_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


def _read_username(payload: Mapping[str, Any], key: str = "username") -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Username is required.")
    username = value.strip()
    if len(username) < USERNAME_MIN_LENGTH:
        raise ValueError(
            f"Username must be at least {USERNAME_MIN_LENGTH} characters."
        )
    if len(username) > USERNAME_MAX_LENGTH:
        raise ValueError(
            f"Username must be {USERNAME_MAX_LENGTH} characters or fewer."
        )
    if any(ch.isspace() for ch in username):
        raise ValueError("Username must not contain whitespace.")
    return username


def _read_new_password(
    payload: Mapping[str, Any],
    key: str = "password",
    label: str = "Password",
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is required.")
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"{label} must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"{label} must be {PASSWORD_MAX_LENGTH} characters or fewer.")
    if value.strip().lower() in COMMON_PASSWORDS:
        raise ValueError(f"{label} is too common. Choose a less predictable one.")
    return value


def _read_existing_password(
    payload: Mapping[str, Any],
    key: str,
    label: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is required.")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"{label} must be {PASSWORD_MAX_LENGTH} characters or fewer.")
    return value


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
class RegisterRequest:
    username: str
    password: str
    remember: bool = False

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RegisterRequest":
        return cls(
            username=_read_username(payload, "username"),
            password=_read_new_password(payload, "password", "Password"),
            remember=_read_required_bool(payload, "remember"),
        )


@dataclass
class UpdateProfileRequest:
    username: str
    current_password: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "UpdateProfileRequest":
        return cls(
            username=_read_username(payload, "username"),
            current_password=_read_existing_password(
                payload, "current_password", "Current password"
            ),
        )


@dataclass
class ChangePasswordRequest:
    current_password: str
    new_password: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ChangePasswordRequest":
        current_password = _read_existing_password(
            payload, "current_password", "Current password"
        )
        new_password = _read_new_password(payload, "new_password", "New password")
        if new_password == current_password:
            raise ValueError("New password must differ from current password.")
        return cls(current_password=current_password, new_password=new_password)


@dataclass
class DeleteConfirmation:
    password: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DeleteConfirmation":
        password = payload.get("password")
        if not isinstance(password, str) or not password:
            raise ValueError("Password is required to confirm deletion.")
        return cls(password=password)
