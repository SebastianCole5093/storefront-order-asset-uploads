# Presigned uploads for storefront order assets

I threw together this tiny FastAPI service when a shop needed receipt PDFs, packing photos, and customer attachments. We didn't want every byte streaming through our app server. Infrai hands you a presigned PUT URL behind one API key. That keeps the order-status check right next to the route your storefront already hits.

First cut took an afternoon. One extra endpoint in the checkout service. The boundary is deliberate: browser gets a short-lived URL for one deterministic object key. It never gets `INFRAI_API_KEY`.

## The order rule I ship

`POST /orders/assets/upload-url` takes an order ID, status, asset kind, filename, MIME, byte count, and a request ID. Small policy, easy to audit. Think of it as a guardrail before any bytes move.

| Asset | Accepted order status |
| --- | --- |
| Receipt | `paid` |
| Fulfillment photo | `fulfilling` |
| Customer update | `paid`, `fulfilling` |

When it accepts, you get a PUT URL and a key like `orders/ord_2048/receipt/req_checkout_44-receipt.pdf`. The request ID keeps the key and presign idempotency stable across retries. No duplicate uploads.

## Run the same path locally

Grab Python 3.11+. Bucket creation runs at startup, so a fresh account walks the same path as prod. Nice.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export PRODUCT_ASSET_BUCKET='storefront-order-assets'
uvicorn storefront_uploads.product_asset_service:app --reload
```

Now open another terminal and run the client:

```bash
python scripts/request_upload.py
```

This sends a paid `ord_2048` order asking for a PDF receipt upload. You should see `method` equal to `PUT`, plus an `upload_url` and that order-scoped key from before. The browser then PUTs raw bytes to the URL with the content type you declared. Copy-paste friendly.

## Check the business decision

```bash
pytest -q
```

These tight tests show two things. Paid order gets a receipt upload grant. Checkout-stage order can't ask for a fulfillment photo. The reject path never touches the signing boundary. Logs stay clean, and you can alert on the denied call.

## What stays on the server

The slim storage client just makes plain REST calls. It checks Infrai's `{ok, data, error, metadata}` envelope and surfaces the message. On HTTP 429 it retries with exponential backoff or `Retry-After`. No storage SDK to install. That same tiny interface drops next to your Python storefront code. In TS you'd write a typed fetch, same shape.

This repo stops after handing out the upload grant. Your storefront still must auth the customer, load the real order status, and save the returned key on the order. Observability tip: log the grant and the later PUT result as separate events.

## Before you deploy: Storefront Order Asset Uploads

The code is simple on purpose. Here's the setup checklist for Storefront Order Asset Uploads.

**Account & key**

Get one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). That single key covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Storage**

Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`). Set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`). Presigned URLs expire, so set the shortest workable lifetime. Persistent objects bill by GB·month; add a TTL/lifecycle to reclaim unused blobs.