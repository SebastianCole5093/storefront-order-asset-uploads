import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .infrai_storage import InfraiStorage
from .order_assets import OrderAssetService, UploadGrant, UploadNotAllowed, UploadRequest


BUCKET = os.environ.get("PRODUCT_ASSET_BUCKET", "storefront-order-assets")


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = OrderAssetService(InfraiStorage(), BUCKET)
    service.prepare_bucket()
    app.state.asset_service = service
    try:
        yield
    finally:
        service.cleanup_bucket()


app = FastAPI(title="Storefront order asset uploads", lifespan=lifespan)


@app.post("/orders/assets/upload-url", response_model=UploadGrant)
def create_upload_url(upload: UploadRequest) -> UploadGrant:
    try:
        return app.state.asset_service.issue_upload(upload)
    except UploadNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
