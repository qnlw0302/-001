from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Product
from .schemas import ProductCreate, ProductUpdate

def insert_product(db: Session, data: ProductCreate) -> Product:
    sku = data.sku.strip()
    name = data.name.strip()

    exists = db.execute(select(Product).where(Product.sku == sku)).scalars().first()
    if exists:
        raise ValueError("SKU already exists")

    p = Product(
        sku=sku,
        name=name,
        stock_qty=data.stock_qty,
        low_stock_threshold=data.low_stock_threshold,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)

def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return db.execute(select(Product).where(Product.sku == sku)).scalars().first()

def delete_product(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()

def update_product(db: Session, product: Product, data: ProductUpdate) -> Product:
    if data.sku is not None:
        new_sku = data.sku.strip()
        if new_sku != product.sku:
            exists = db.execute(select(Product).where(Product.sku == new_sku)).scalars().first()
            if exists:
                raise ValueError("SKU already exists")
            product.sku = new_sku

    if data.name is not None:
        product.name = data.name.strip()

    if data.stock_qty is not None:
        product.stock_qty = data.stock_qty

    if data.low_stock_threshold is not None:
        product.low_stock_threshold = data.low_stock_threshold

    db.commit()
    db.refresh(product)
    return product

def list_all_products(db: Session) -> list[Product]:
    stmt = select(Product).order_by(Product.id.desc())
    return db.execute(stmt).scalars().all()