from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


LOW_STOCK_THRESHOLD = 5


def _read_required_text(payload: Mapping[str, Any], key: str, label: str, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")

    text = value.strip()
    if len(text) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer.")
    return text


def _read_optional_text(payload: Mapping[str, Any], key: str, label: str, max_length: int) -> str | None:
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


def _read_optional_int(payload: Mapping[str, Any], key: str, label: str) -> int | None:
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


@dataclass
class Product:
    id: int
    sku: str
    name: str
    stock_qty: int
    low_stock_threshold: int = LOW_STOCK_THRESHOLD

    @property
    def status(self) -> str:
        if self.stock_qty <= 0:
            return "out"
        if self.stock_qty <= self.low_stock_threshold:
            return "low"
        return "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "stock_qty": self.stock_qty,
            "low_stock_threshold": self.low_stock_threshold,
            "status": self.status,
        }


@dataclass
class ProductCreate:
    sku: str
    name: str
    stock_qty: int = 0
    low_stock_threshold: int = LOW_STOCK_THRESHOLD

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProductCreate":
        return cls(
            sku=_read_required_text(payload, "sku", "SKU", 64),
            name=_read_required_text(payload, "name", "Product name", 200),
            stock_qty=_read_required_int(payload, "stock_qty", "Stock quantity"),
            low_stock_threshold=LOW_STOCK_THRESHOLD,
        )


@dataclass
class ProductUpdate:
    sku: str | None = None
    name: str | None = None
    stock_qty: int | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProductUpdate":
        update = cls(
            sku=_read_optional_text(payload, "sku", "SKU", 64),
            name=_read_optional_text(payload, "name", "Product name", 200),
            stock_qty=_read_optional_int(payload, "stock_qty", "Stock quantity"),
        )
        if update.sku is None and update.name is None and update.stock_qty is None:
            raise ValueError("At least one field is required for update.")
        return update
