from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol


class OrderStatus(str, Enum):
    CHECKOUT = "checkout"
    PAID = "paid"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"


class AssetKind(str, Enum):
    RECEIPT = "receipt"
    FULFILLMENT_PHOTO = "fulfillment_photo"
    CUSTOMER_UPDATE = "customer_update"


@dataclass
class UploadRequest:
    order_id: str
    order_status: OrderStatus
    asset_kind: AssetKind
    filename: str
    content_type: str
    size_bytes: int
    request_id: str

    def __post_init__(self) -> None:
        self.order_status = OrderStatus(self.order_status)
        self.asset_kind = AssetKind(self.asset_kind)
        patterns = {
            "order_id": r"^[A-Za-z0-9_-]{3,64}$",
            "filename": r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$",
            "content_type": r"^(image/(jpeg|png|webp)|application/pdf)$",
            "request_id": r"^[A-Za-z0-9_-]{8,80}$",
        }
        for field, pattern in patterns.items():
            if not re.fullmatch(pattern, getattr(self, field)):
                raise ValueError(f"invalid {field}")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool):
            raise ValueError("size_bytes must be an integer")
        if not 0 < self.size_bytes <= 10_000_000:
            raise ValueError("size_bytes must be between 1 and 10000000")


@dataclass
class UploadGrant:
    order_id: str
    asset_kind: AssetKind
    object_key: str
    upload_url: str
    method: str = "PUT"
    expires_seconds: int = 600


class StoragePort(Protocol):
    def create_bucket(self, name: str) -> dict: ...

    def delete_bucket(self, name: str) -> dict: ...

    def presign_put(
        self, bucket: str, key: str, content_type: str, max_bytes: int, idempotency_key: str
    ) -> dict: ...


ALLOWED_STATUSES = {
    AssetKind.RECEIPT: {OrderStatus.PAID},
    AssetKind.FULFILLMENT_PHOTO: {OrderStatus.FULFILLING},
    AssetKind.CUSTOMER_UPDATE: {OrderStatus.PAID, OrderStatus.FULFILLING},
}


class UploadNotAllowed(ValueError):
    pass


class OrderAssetService:
    def __init__(self, storage: StoragePort, bucket: str) -> None:
        self.storage = storage
        self.bucket = bucket

    def prepare_bucket(self) -> None:
        self.storage.create_bucket(self.bucket)

    def cleanup_bucket(self) -> None:
        self.storage.delete_bucket(self.bucket)

    def issue_upload(self, upload: UploadRequest) -> UploadGrant:
        if upload.order_status not in ALLOWED_STATUSES[upload.asset_kind]:
            raise UploadNotAllowed(
                f"{upload.asset_kind.value} is not accepted while order is {upload.order_status.value}"
            )
        key = f"orders/{upload.order_id}/{upload.asset_kind.value}/{upload.request_id}-{upload.filename}"
        signed = self.storage.presign_put(
            self.bucket,
            key,
            upload.content_type,
            upload.size_bytes,
            f"order-upload-{upload.request_id}",
        )
        return UploadGrant(
            order_id=upload.order_id,
            asset_kind=upload.asset_kind,
            object_key=key,
            upload_url=signed["url"],
        )
