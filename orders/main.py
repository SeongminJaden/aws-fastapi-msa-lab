import os
import sqlite3
from contextlib import asynccontextmanager, closing
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "orders.db")
PRODUCT_URL = os.getenv("PRODUCT_URL", "http://localhost:8001")


@asynccontextmanager
async def lifespan(app):
    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, product_id INTEGER, product_name TEXT, quantity INTEGER, unit_price INTEGER, total INTEGER)")
    yield


app = FastAPI(title="주문 서비스 · AWS 특강", lifespan=lifespan)


class OrderInput(BaseModel):
    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(ge=1, le=100, strict=True)


def fetch_product(path):
    try:
        response = httpx.get(PRODUCT_URL + path, timeout=3.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, "상품을 찾을 수 없습니다") from exc
        raise HTTPException(503, "상품 서비스 응답 오류") from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(503, "상품 서비스에 연결할 수 없습니다") from exc


@app.get("/health")
def health():
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.execute("SELECT 1 FROM orders LIMIT 1")
    return {"status": "ok", "service": "orders"}


@app.get("/products")
def products():
    return fetch_product("/products")


@app.post("/orders", status_code=201)
def create_order(body: OrderInput):
    product = fetch_product(f"/products/{body.product_id}")
    order = dict(id=str(uuid4()), product_id=product["id"], product_name=product["name"],
                 quantity=body.quantity, unit_price=product["price"], total=product["price"] * body.quantity)
    # ponytail: 단일 EC2·단일 주문 컨테이너용 SQLite. 복제 배포는 전용 PostgreSQL로 전환합니다.
    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", tuple(order.values()))
    return order


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "주문을 찾을 수 없습니다")
    return dict(row)
