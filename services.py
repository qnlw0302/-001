from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import crud
from schemas import (
    MOVEMENT_TYPES,
    MovementRequest,
    Product,
    ProductCreate,
    ProductUpdate,
    StockMovement,
    User,
)


class AccountLockedError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Account is temporarily locked.")
        self.retry_after_seconds = retry_after_seconds


class InventoryService:
    """Thin façade around the crud layer. Routes use this; routes never touch sqlite3."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        request_ip: Optional[str] = None,
        max_login_attempts: int = 5,
        lockout_seconds: int = 900,
    ) -> None:
        self._connection = connection
        self._request_ip = request_ip
        self._max_login_attempts = max_login_attempts
        self._lockout_seconds = lockout_seconds

    # ---------- products ----------
    def list_products(
        self,
        user_id: int,
        search: str = "",
        page: int = 1,
        limit: int = 10,
    ) -> Dict[str, Any]:
        return crud.list_products(
            self._connection,
            user_id=user_id,
            search=search,
            page=page,
            limit=limit,
        )

    def get_product(self, user_id: int, product_id: int) -> Optional[Product]:
        return crud.get_product(self._connection, user_id, product_id)

    def insert_product(self, user_id: int, data: ProductCreate) -> Product:
        product = crud.insert_product(self._connection, user_id, data)
        self._audit(
            user_id,
            "product.create",
            entity_type="product",
            entity_id=product.id,
            details={"sku": product.sku, "name": product.name},
        )
        # Seed a synthetic `receive` movement so the history isn't missing the
        # initial stock — keeps `list_movements` a complete ledger from day one.
        if product.stock_qty > 0:
            crud.insert_stock_movement(
                self._connection,
                user_id=user_id,
                product_id=product.id,
                movement_type="receive",
                quantity_delta=product.stock_qty,
                quantity_after=product.stock_qty,
                note="Initial stock on create",
            )
        return product

    def update_product(
        self,
        user_id: int,
        product_id: int,
        data: ProductUpdate,
    ) -> Product:
        product = crud.update_product(self._connection, user_id, product_id, data)
        self._audit(
            user_id,
            "product.update",
            entity_type="product",
            entity_id=product.id,
            details={"sku": product.sku, "name": product.name},
        )
        return product

    def delete_product(self, user_id: int, product_id: int) -> bool:
        current = crud.get_product(self._connection, user_id, product_id)
        deleted = crud.delete_product(self._connection, user_id, product_id)
        if deleted and current is not None:
            self._audit(
                user_id,
                "product.delete",
                entity_type="product",
                entity_id=product_id,
                details={"sku": current.sku, "name": current.name},
            )
        return deleted

    def iter_all_products(self, user_id: int) -> Iterator[Product]:
        return crud.iter_all_products(self._connection, user_id)

    # ---------- stock movements ----------
    def record_movement(
        self,
        user_id: int,
        product_id: int,
        data: MovementRequest,
    ) -> Tuple[StockMovement, Product]:
        """Apply a stock movement and update the product's `stock_qty` atomically
        from the caller's perspective. Owns the sign convention so callers always
        send a positive magnitude (except for `adjust`, which is an absolute level).
        """
        product = crud.get_product(self._connection, user_id, product_id)
        if product is None:
            raise LookupError("Product not found.")

        if data.movement_type == "adjust":
            new_qty = data.quantity
            delta = new_qty - product.stock_qty
        elif data.movement_type in ("receive", "return"):
            delta = data.quantity
            new_qty = product.stock_qty + delta
        elif data.movement_type in ("remove", "damaged"):
            delta = -data.quantity
            new_qty = product.stock_qty + delta
            if new_qty < 0:
                raise ValueError(
                    f"Cannot {data.movement_type} {data.quantity} units: "
                    f"only {product.stock_qty} in stock."
                )
        else:
            # MovementRequest already validates against MOVEMENT_TYPES, so this
            # branch is unreachable; keep it explicit so the type checker / a
            # future contributor doesn't quietly fall through.
            raise ValueError(f"Unsupported movement type: {data.movement_type}")

        crud.set_product_stock(self._connection, user_id, product_id, new_qty)
        movement = crud.insert_stock_movement(
            self._connection,
            user_id=user_id,
            product_id=product_id,
            movement_type=data.movement_type,
            quantity_delta=delta,
            quantity_after=new_qty,
            note=data.note,
        )
        self._audit(
            user_id,
            f"stock.{data.movement_type}",
            entity_type="product",
            entity_id=product_id,
            details={
                "delta": delta,
                "after": new_qty,
                "sku": product.sku,
                "note": data.note,
            },
        )
        refreshed = crud.get_product(self._connection, user_id, product_id)
        if refreshed is None:
            raise RuntimeError("Product disappeared after stock movement.")
        return movement, refreshed

    def list_movements(
        self,
        user_id: int,
        product_id: int,
        limit: int = 50,
    ) -> List[StockMovement]:
        product = crud.get_product(self._connection, user_id, product_id)
        if product is None:
            raise LookupError("Product not found.")
        return crud.list_stock_movements(self._connection, user_id, product_id, limit=limit)

    # ---------- users ----------
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return crud.get_user_by_id(self._connection, user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return crud.get_user_by_username(self._connection, username)

    def count_users(self) -> int:
        return crud.count_users(self._connection)

    def create_user(self, username: str, password_hash: str) -> User:
        user = crud.create_user(self._connection, username, password_hash)
        self._audit(user.id, "user.register", entity_type="user", entity_id=user.id)
        return user

    def update_user_username(self, user_id: int, new_username: str) -> User:
        user = crud.update_user_username(self._connection, user_id, new_username)
        self._audit(
            user_id,
            "user.update_profile",
            entity_type="user",
            entity_id=user_id,
            details={"username": new_username},
        )
        return user

    def update_user_password(self, user_id: int, new_password_hash: str) -> None:
        crud.update_user_password(self._connection, user_id, new_password_hash)
        self._audit(user_id, "user.change_password", entity_type="user", entity_id=user_id)

    def get_password_hash(self, user_id: int) -> Optional[str]:
        return crud.get_password_hash(self._connection, user_id)

    # ---------- login lockout ----------
    def check_account_lock(self, username: str) -> Optional[Dict[str, Any]]:
        """Return lock state if the user exists and is currently locked, else None."""
        state = crud.get_login_lock_state(self._connection, username)
        if state is None:
            return None
        retry_after = self._lock_retry_seconds(state.get("locked_until"))
        if retry_after <= 0:
            return None
        return {"user_id": state["id"], "retry_after_seconds": retry_after}

    def record_failed_login(self, user_id: int) -> Dict[str, Any]:
        result = crud.record_failed_login(
            self._connection,
            user_id,
            max_attempts=self._max_login_attempts,
            lockout_seconds=self._lockout_seconds,
        )
        self._audit(
            user_id,
            "auth.login_failed",
            entity_type="user",
            entity_id=user_id,
            details={"failed_login_count": result.get("failed_login_count")},
        )
        return result

    def reset_failed_logins(self, user_id: int) -> None:
        crud.reset_failed_logins(self._connection, user_id)

    def record_login(self, user_id: int) -> None:
        self._audit(user_id, "auth.login", entity_type="user", entity_id=user_id)

    def record_logout(self, user_id: int) -> None:
        self._audit(user_id, "auth.logout", entity_type="user", entity_id=user_id)

    # ---------- audit ----------
    def list_audit_events(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        return crud.list_audit_events(self._connection, user_id, limit=limit)

    # ---------- internals ----------
    def _audit(
        self,
        user_id: Optional[int],
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        crud.write_audit_event(
            self._connection,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=self._request_ip,
        )

    def _lock_retry_seconds(self, locked_until: Optional[str]) -> int:
        if not locked_until:
            return 0
        try:
            expires_at = datetime.fromisoformat(locked_until)
        except ValueError:
            return 0
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = (expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(delta) + 1)
