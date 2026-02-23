"""
产品列表，可以看得到当前库存，阈值和状态（正常、低库存、缺货）。可以添加新产品，编辑现有产品的库存和阈值，以及删除产品。
"""
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import crud
from .schemas import ProductCreate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="库存管理")
templates = Jinja2Templates(directory="app/templates")

def status_label(stock: int, threshold: int) -> str:
    if stock == 0:
        return "缺货"
    if stock <= threshold:
        return "低库存"
    return "正常"