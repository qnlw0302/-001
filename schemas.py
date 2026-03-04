from pydantic import BaseModel, Field, ConfigDict
class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    stock_qty: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    stock_qty: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)

class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int