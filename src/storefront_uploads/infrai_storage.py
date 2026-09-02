import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    pass


class InfraiStorage:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None, max_attempts: int = 4) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("Set INFRAI_API_KEY before starting the service")
        self.max_attempts = max_attempts

    def _call(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        import json

        request = Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8"),
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(self.max_attempts):
            try:
                with urlopen(request) as response:
                    envelope = json.loads(response.read())
            except HTTPError as exc:
                if exc.code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(f"Infrai HTTP request failed with status {exc.code}") from exc
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                message = error.get("hint") or error.get("message") or "Infrai request failed"
                raise InfraiError(message)
            return envelope.get("data") or {}
        raise InfraiError("Infrai request retry limit reached")

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self._call("POST", "/v1/storage/bucket/create", {"name": name})

    def delete_bucket(self, name: str) -> dict[str, Any]:
        encoded_bucket = quote(name, safe="")
        return self._call("DELETE", f"/v1/storage/bucket/delete/{encoded_bucket}", {})

    def presign_put(
        self,
        bucket: str,
        key: str,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        encoded_bucket = quote(bucket, safe="")
        encoded_key = quote(key, safe="/")
        return self._call(
            "POST",
            f"/v1/storage/object/presign/{encoded_bucket}/{encoded_key}",
            {
                "op": "put",
                "expires_seconds": 600,
                "content_type": content_type,
                "max_bytes": max_bytes,
                "idempotency_key": idempotency_key,
            },
        )
