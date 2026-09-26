"""Vercel Blob storage backend for Django media files.

Vercel serverless filesystems are read-only (`/var/task`), so `MEDIA_ROOT`
writes fail with OSError. When ``BLOB_READ_WRITE_TOKEN`` is set, media is
stored in a Vercel Blob store instead and ``FieldFile.url`` returns the public
blob URL.

Auth: static read-write token only (OIDC is not used by this thin REST client).
Create a **public** Blob store so images can be embedded without a proxy.
"""

from __future__ import annotations

import mimetypes
import os

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils import timezone
from django.utils.deconstruct import deconstructible

API_BASE = "https://blob.vercel-storage.com"
API_VERSION = "10"
DEFAULT_CACHE_MAX_AGE = "31536000"
REQUEST_TIMEOUT = 30


class VercelBlobError(OSError):
    """Raised when a Vercel Blob API call fails (maps to storage I/O errors)."""


def _store_id_from_token(token: str) -> str:
    # Token shape: vercel_blob_rw_store_<id>_<secret>
    parts = (token or "").split("_")
    if len(parts) >= 4 and parts[0] == "vercel" and parts[2] == "rw":
        return "store_" + parts[3]
    return ""


def _normalize_store_id(store_id: str) -> str:
    return (store_id or "").strip()


@deconstructible
class VercelBlobStorage(Storage):
    """Django storage that persists uploads to Vercel Blob."""

    def __init__(self, token=None, access=None, public_base_url=None, store_id=None, timeout=REQUEST_TIMEOUT):
        self.token = (token if token is not None else os.getenv("BLOB_READ_WRITE_TOKEN", "")).strip()
        if not self.token:
            raise ValueError(
                "VercelBlobStorage requires BLOB_READ_WRITE_TOKEN "
                "(create a public Blob store in the Vercel dashboard)."
            )
        self.access = (access or os.getenv("BLOB_ACCESS", "public") or "public").strip().lower()
        if self.access not in {"public", "private"}:
            raise ValueError("BLOB_ACCESS must be 'public' or 'private'")
        self.timeout = timeout

        self.public_base_url = (
            public_base_url if public_base_url is not None else os.getenv("BLOB_PUBLIC_URL", "")
        ).strip().rstrip("/")
        if not self.public_base_url:
            resolved = _normalize_store_id(
                store_id if store_id is not None else os.getenv("BLOB_STORE_ID", "")
            ) or _store_id_from_token(self.token)
            if resolved:
                self.public_base_url = (
                    f"https://{resolved}.{self.access}.blob.vercel-storage.com"
                )
        if not self.public_base_url:
            raise ValueError(
                "Cannot derive blob public URL. Set BLOB_PUBLIC_URL or BLOB_STORE_ID."
            )

    # --- HTTP helpers -------------------------------------------------

    def _auth_headers(self, **extra) -> dict:
        headers = {
            "authorization": f"Bearer {self.token}",
            "x-api-version": API_VERSION,
        }
        headers.update(extra)
        return headers

    def _public_url(self, name: str) -> str:
        return f"{self.public_base_url}/{str(name).lstrip('/')}"

    def _head_meta(self, name: str) -> dict | None:
        """Return blob metadata, or None when missing."""
        url = self._public_url(name)
        try:
            resp = requests.get(
                f"{API_BASE}/",
                params={"url": url},
                headers=self._auth_headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VercelBlobError(f"Vercel Blob head failed: {exc}") from exc
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (404, 400):
            return None
        raise VercelBlobError(
            f"Vercel Blob head failed ({resp.status_code}): {resp.text[:300]}"
        )

    def _content_type(self, name: str, content=None) -> str:
        guessed = getattr(content, "content_type", None)
        if guessed:
            return guessed
        content_type, _ = mimetypes.guess_type(name)
        return content_type or "application/octet-stream"

    # --- Storage API --------------------------------------------------

    def _open(self, name, mode="rb"):
        if any(flag in mode for flag in ("w", "a", "+")):
            raise ValueError("VercelBlobStorage.open() is read-only; use save() to write.")
        url = self._public_url(name)
        headers = {}
        if self.access == "private":
            headers = self._auth_headers()
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise VercelBlobError(f"Vercel Blob download failed: {exc}") from exc
        if resp.status_code != 200:
            raise FileNotFoundError(f"Blob not found: {name}")
        return ContentFile(resp.content, name=name)

    def _save(self, name, content):
        pathname = str(name).replace("\\", "/").lstrip("/")
        data = b"".join(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8")
                        for chunk in content.chunks())
        headers = self._auth_headers(
            access=self.access,
            **{
                "x-content-type": self._content_type(pathname, content),
                "x-cache-control-max-age": DEFAULT_CACHE_MAX_AGE,
                # Django's get_available_name already uniquified; allow overwrite
                # so a race between exists() and put() does not 500 the admin.
                "x-allow-overwrite": "1",
            },
        )
        try:
            resp = requests.put(
                f"{API_BASE}/",
                params={"pathname": pathname},
                headers=headers,
                data=data,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VercelBlobError(f"Vercel Blob upload failed: {exc}") from exc
        if resp.status_code != 200:
            raise VercelBlobError(
                f"Vercel Blob upload failed ({resp.status_code}): {resp.text[:500]}"
            )
        meta = resp.json()
        return meta.get("pathname") or pathname

    def delete(self, name):
        url = self._public_url(name)
        try:
            resp = requests.post(
                f"{API_BASE}/delete",
                headers=self._auth_headers(),
                json={"urls": [url]},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VercelBlobError(f"Vercel Blob delete failed: {exc}") from exc
        if resp.status_code not in (200, 404):
            raise VercelBlobError(
                f"Vercel Blob delete failed ({resp.status_code}): {resp.text[:300]}"
            )

    def exists(self, name):
        return self._head_meta(name) is not None

    def size(self, name):
        meta = self._head_meta(name)
        if meta is None:
            raise VercelBlobError(f"Blob not found: {name}")
        return int(meta.get("size") or 0)

    def url(self, name):
        return self._public_url(name)

    def listdir(self, path):
        path = str(path).replace("\\", "/").strip("/")
        prefix = f"{path}/" if path else ""
        directories = set()
        files = []
        cursor = None
        while True:
            params = {"limit": "1000", "prefix": prefix}
            if cursor:
                params["cursor"] = cursor
            try:
                resp = requests.get(
                    f"{API_BASE}/",
                    params=params,
                    headers=self._auth_headers(),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise VercelBlobError(f"Vercel Blob list failed: {exc}") from exc
            if resp.status_code != 200:
                raise VercelBlobError(
                    f"Vercel Blob list failed ({resp.status_code}): {resp.text[:300]}"
                )
            payload = resp.json()
            for blob in payload.get("blobs") or []:
                full = (blob.get("pathname") or "").lstrip("/")
                if prefix and not full.startswith(prefix):
                    continue
                rest = full[len(prefix):]
                if not rest:
                    continue
                if "/" in rest:
                    directories.add(rest.split("/", 1)[0])
                else:
                    files.append(rest)
            cursor = payload.get("cursor")
            if not payload.get("hasMore") or not cursor:
                break
        return sorted(directories), files

    def get_created_time(self, name):
        from django.utils import timezone

        meta = self._head_meta(name)
        if meta is None or not meta.get("uploadedAt"):
            raise VercelBlobError(f"Blob not found: {name}")
        return timezone.datetime.fromisoformat(
            str(meta["uploadedAt"]).replace("Z", "+00:00")
        )

    get_modified_time = get_created_time
    get_accessed_time = get_created_time

    def get_available_name(self, name, max_length=None):
        return name

    def get_filename(self, name):
        return name

    def path(self, name):
        return ""


class NoOpStorage(Storage):
    """No-op storage for Vercel serverless environment when no blob token is set.

    Prevents OSError on read-only /var/task filesystem by silently
    discarding uploaded files. Existing media URLs are returned as-is.
    """

    def _save(self, name, content):
        return name

    def _open(self, name, mode='rb'):
        from django.core.files.base import ContentFile
        return ContentFile(b'')

    def delete(self, name):
        pass

    def exists(self, name):
        return False

    def url(self, name):
        return name

    def size(self, name):
        return 0

    def get_created_time(self, name):
        return timezone.now()

    def get_valid_name(self, name):
        return name

    def get_available_name(self, name, max_length=None):
        return name

    def get_filename(self, name):
        return name

    def path(self, name):
        return ''

