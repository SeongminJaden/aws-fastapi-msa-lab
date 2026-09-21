from fastapi import FastAPI, HTTPException

app = FastAPI(title="상품 서비스")
# ponytail: 읽기 전용 상품 3개. 상품 수정 실습을 추가할 때 전용 DB로 바꿉니다.
PRODUCTS = {
    1: {"id": 1, "name": "AWS 노트", "price": 5000},
    2: {"id": 2, "name": "Docker 스티커", "price": 2000},
    3: {"id": 3, "name": "KANT 머그컵", "price": 12000},
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "products"}


@app.get("/products")
def products():
    return list(PRODUCTS.values())


@app.get("/products/{product_id}")
def product(product_id: int):
    if product_id not in PRODUCTS:
        raise HTTPException(404, "상품을 찾을 수 없습니다")
    return PRODUCTS[product_id]
