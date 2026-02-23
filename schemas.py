from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str | None = None
    supplier: str | None = None
    cost_price: float | None = None
    sale_price: float | None = None
    stock_qty: int = 0
    low_stock_threshold: int = 10
    location: str | None = None

class MovementCreate(BaseModel):
    qty: int = Field(gt=0)
    note: str | None = None