"""python -m unittest -v: AWS·Docker 없이 API 계약과 저장 동작을 검증합니다."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / name / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FlowTest(unittest.TestCase):
    def test_order_flow(self):
        products, orders = load("products"), load("orders")
        with tempfile.TemporaryDirectory() as directory:
            orders.DB_PATH = str(Path(directory) / "orders.db")
            with TestClient(products.app) as catalog, TestClient(orders.app) as client:
                def request(url, **kwargs):
                    return catalog.get(url.removeprefix(orders.PRODUCT_URL))

                with patch.object(orders.httpx, "get", side_effect=request):
                    self.assertEqual(len(client.get("/products").json()), 3)
                    response = client.post("/orders", json={"product_id": 1, "quantity": 2})
                    self.assertEqual(response.status_code, 201)
                    order = response.json()
                    self.assertEqual(order["total"], 10000)
                    self.assertEqual(client.get('/orders/' + order['id']).json(), order)
                    self.assertEqual(client.post("/orders", json={"product_id": 999, "quantity": 1}).status_code, 404)
                    for quantity in (0, 101, "2"):
                        self.assertEqual(client.post("/orders", json={"product_id": 1, "quantity": quantity}).status_code, 422)
                with patch.object(orders.httpx, "get", side_effect=httpx.ConnectError("offline")):
                    self.assertEqual(client.post("/orders", json={"product_id": 1, "quantity": 1}).status_code, 503)
                    self.assertEqual(client.get('/orders/' + order['id']).status_code, 200)
            with TestClient(orders.app) as restarted:
                self.assertEqual(restarted.get('/orders/' + order['id']).json(), order)
                self.assertEqual(restarted.get('/orders/not-found').status_code, 404)


if __name__ == "__main__":
    unittest.main()
