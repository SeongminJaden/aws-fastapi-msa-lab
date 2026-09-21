"""실행 중인 Compose/EC2 확인: python smoke.py http://localhost:8000"""
import json
import sys
from urllib.request import Request, urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    with urlopen(Request(base + path, data=data, headers={"Content-Type": "application/json"}), timeout=10) as response:
        return response.status, json.load(response)


assert request("/health")[0] == 200
assert len(request("/products")[1]) == 3
status, order = request("/orders", {"product_id": 1, "quantity": 2})
assert status == 201 and order["total"] == 10000
assert request("/orders/" + order["id"])[1] == order
print("PASS: 상품 조회 → 주문 생성(10,000원) → 주문 조회", order["id"])
