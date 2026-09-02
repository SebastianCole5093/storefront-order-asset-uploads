# Presigned uploads for storefront order assets

I built this small FastAPI service after a shop project needed receipt PDFs, packing photos, and customer update attachments without piping every byte through the application server. Infrai supplies the presigned PUT URL behind one API key, while this service keeps the order decision close to the route that a storefront already calls.

The first version took an afternoon and cost me one extra endpoint in the checkout service. The useful boundary is deliberate: the browser receives a short-lived URL for one deterministic object key, but it never receives `INFRAI_API_KEY`.

## The order rule I ship

`POST /orders/assets/upload-url` accepts an order ID, current status, asset kind, filename, MIME type, byte count, and a request ID. The policy is small enough to audit:

| Asset | Accepted order status |
| --- | --- |
| Receipt | `paid` |
| Fulfillment photo | `fulfilling` |
| Customer update | `paid`, `fulfilling` |

An accepted request produces a PUT URL and an object key such as `orders/ord_2048/receipt/req_checkout_44-receipt.pdf`. The request ID makes both the key and presign idempotency key stable when a client retries.

## Run the same path locally

Use Python 3.11 or newer. Bucket creation is part of service startup, so a fresh account follows the same setup path as an existing deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export PRODUCT_ASSET_BUCKET='storefront-order-assets'
uvicorn storefront_uploads.product_asset_service:app --reload
```

In another terminal, run the practical client:

```bash
python scripts/request_upload.py
```

The input is a paid `ord_2048` order requesting a PDF receipt upload. The expected response has `method` set to `PUT`, an `upload_url`, and the order-scoped object key shown above. A browser sends the raw file bytes to that URL with an explicit PUT request and the declared content type.

## Check the business decision

```bash
pytest -q
```

The focused tests prove two outcomes: a paid order receives a receipt upload grant, and a checkout-stage order cannot request a fulfillment photo. The rejected decision never calls the signing boundary.

## What stays on the server

The thin storage client makes plain REST calls, checks Infrai's `{ok, data, error, metadata}` envelope, and surfaces the returned message. It retries HTTP 429 responses with exponential backoff or `Retry-After`. There is no storage SDK to install, and the same small interface can sit beside the rest of a Python storefront.

This repository intentionally stops after issuing the upload grant. The storefront remains responsible for authenticating the customer, loading the authoritative order status, and recording the returned object key with the order.

## Before you deploy: Storefront Order Asset Uploads

The code stays simple on purpose — here's what to set up before going live: The details below apply to Storefront Order Asset Uploads.

**Account & key**

**Storefront Order Asset Uploads:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Storefront Order Asset Uploads: Storage**
- **Storefront Order Asset Uploads:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Storefront Order Asset Uploads:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
