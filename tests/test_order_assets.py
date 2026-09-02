import pytest

from storefront_uploads.order_assets import OrderAssetService, UploadNotAllowed, UploadRequest


class RecordingStorage:
    def __init__(self) -> None:
        self.presign_calls = []

    def create_bucket(self, name: str) -> dict:
        return {"name": name}

    def delete_bucket(self, name: str) -> dict:
        return {"name": name}

    def presign_put(self, bucket, key, content_type, max_bytes, idempotency_key) -> dict:
        self.presign_calls.append((bucket, key, content_type, max_bytes, idempotency_key))
        return {"url": "https://uploads.example/signed-order-asset"}


def test_paid_order_gets_a_receipt_upload_scoped_to_its_order() -> None:
    storage = RecordingStorage()
    service = OrderAssetService(storage, "storefront-order-assets")
    grant = service.issue_upload(
        UploadRequest(
            order_id="ord_2048",
            order_status="paid",
            asset_kind="receipt",
            filename="receipt.pdf",
            content_type="application/pdf",
            size_bytes=240_000,
            request_id="req_checkout_44",
        )
    )

    assert grant.method == "PUT"
    assert grant.object_key == "orders/ord_2048/receipt/req_checkout_44-receipt.pdf"
    assert storage.presign_calls[0][4] == "order-upload-req_checkout_44"


def test_checkout_order_cannot_attach_a_fulfillment_photo() -> None:
    storage = RecordingStorage()
    service = OrderAssetService(storage, "storefront-order-assets")

    with pytest.raises(UploadNotAllowed, match="fulfillment_photo"):
        service.issue_upload(
            UploadRequest(
                order_id="ord_2048",
                order_status="checkout",
                asset_kind="fulfillment_photo",
                filename="parcel.jpg",
                content_type="image/jpeg",
                size_bytes=400_000,
                request_id="req_fulfill_44",
            )
        )

    assert storage.presign_calls == []
