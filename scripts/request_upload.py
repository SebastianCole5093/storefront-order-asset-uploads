import json
from urllib.request import Request, urlopen


payload = {
    "order_id": "ord_2048",
    "order_status": "paid",
    "asset_kind": "receipt",
    "filename": "receipt.pdf",
    "content_type": "application/pdf",
    "size_bytes": 240000,
    "request_id": "req_checkout_44",
}
request = Request(
    "http://127.0.0.1:8000/orders/assets/upload-url",
    data=json.dumps(payload).encode("utf-8"),
    method="POST",
    headers={"Content-Type": "application/json"},
)
with urlopen(request) as response:
    print(json.dumps(json.loads(response.read()), indent=2))
