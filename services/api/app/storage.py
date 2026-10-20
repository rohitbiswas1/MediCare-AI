from pathlib import Path
import io
import socket
import struct
import warnings
import httpx
import pymupdf as fitz
from PIL import Image
import pydicom
from cryptography.fernet import Fernet
from fastapi import HTTPException
from .config import settings

Image.MAX_IMAGE_PIXELS = 25_000_000
ALLOWED = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png", "application/dicom": ".dcm"}


def scan_malware(data: bytes):
    cfg = settings()
    if not cfg.clamav_host:
        if cfg.production:
            raise HTTPException(503, "Malware scanning is required before uploads can be accepted.")
        return "structural_checks_only"
    try:
        with socket.create_connection((cfg.clamav_host, cfg.clamav_port), timeout=15) as sock:
            sock.sendall(b"zINSTREAM\0")
            for start in range(0, len(data), 65536):
                chunk = data[start : start + 65536]
                sock.sendall(struct.pack("!I", len(chunk)) + chunk)
            sock.sendall(struct.pack("!I", 0))
            result = sock.recv(4096)
        if b"FOUND" in result:
            raise HTTPException(422, "The file failed the malware safety check.")
        if not result.endswith(b"OK\x00") and not result.endswith(b"OK\n"):
            raise HTTPException(503, "Malware scanner could not verify this upload.")
    except OSError:
        raise HTTPException(503, "Malware scanner is unavailable. Please retry later.")
    return "clamav_passed"


def validate_file(data: bytes, filename: str):
    if not data or len(data) > settings().max_upload_bytes:
        raise HTTPException(413, "Upload a nonempty file no larger than 15 MB.")
    suffix = Path(filename).suffix.lower()
    try:
        if data.startswith(b"%PDF-") and suffix == ".pdf":
            with fitz.open(stream=data, filetype="pdf") as pdf:
                if pdf.is_encrypted or len(pdf) > 20 or len(pdf) == 0:
                    raise ValueError("PDF must be unencrypted and contain 1–20 pages.")
                forbidden = (
                    "/JavaScript",
                    "/JS ",
                    "/Launch",
                    "/EmbeddedFile",
                    "/RichMedia",
                    "/OpenAction",
                    "/AA ",
                )
                for idx in range(1, pdf.xref_length()):
                    obj = pdf.xref_object(idx)
                    if any(token in obj for token in forbidden):
                        raise ValueError("Active content or attachments are not supported.")
            mime = "application/pdf"
        elif suffix in {".png", ".jpg", ".jpeg"}:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if image.format not in {"PNG", "JPEG"} or image.width < 32 or image.height < 32:
                        raise ValueError("Upload a readable PNG or JPEG image.")
                    mime = "image/png" if image.format == "PNG" else "image/jpeg"
                    if (mime == "image/png") != (suffix == ".png"):
                        raise ValueError("The file extension does not match its content.")
                    image.verify()
        elif suffix == ".dcm" and len(data) > 132 and data[128:132] == b"DICM":
            doc = pydicom.dcmread(io.BytesIO(data), stop_before_pixels=True)
            if str(doc.get("Modality", "")) not in {"CR", "DX"}:
                raise ValueError("Only chest radiography DICOM containers (CR/DX) are supported.")
            if int(doc.get("Rows", 0)) * int(doc.get("Columns", 0)) > 25_000_000:
                raise ValueError("DICOM dimensions exceed the safety limit.")
            if int(doc.get("NumberOfFrames", 1)) != 1:
                raise ValueError("Multi-frame DICOM is not supported.")
            mime = "application/dicom"
        else:
            raise ValueError("Supported uploads: PDF, PNG, JPEG, and single-frame CR/DX DICOM.")
    except HTTPException:
        raise
    except Exception as exc:
        # Parser errors may include document content; expose only controlled validation messages.
        safe = str(exc) if type(exc) is ValueError else "The document is damaged or unsupported."
        raise HTTPException(422, safe)
    return mime, scan_malware(data)


class Storage:
    def __init__(self):
        self.cfg = settings()

    def _path(self, key):
        root = (Path(self.cfg.local_data_dir) / "documents").resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Invalid storage key")
        return path

    def _remote(self, method, key, data=None):
        cfg = self.cfg
        if not cfg.supabase_url or not cfg.supabase_service_role_key:
            raise HTTPException(503, "Private storage is not configured.")
        headers = {
            "apikey": cfg.supabase_service_role_key,
            "Authorization": f"Bearer {cfg.supabase_service_role_key}",
            "Content-Type": "application/octet-stream",
        }
        try:
            base = f"{cfg.supabase_url}/storage/v1/object/{cfg.supabase_storage_bucket}"
            if method == "DELETE":
                headers["Content-Type"] = "application/json"
                result = httpx.request(method, base, json={"prefixes": [key]}, headers=headers, timeout=30)
            else:
                result = httpx.request(method, f"{base}/{key}", content=data, headers=headers, timeout=30)
        except httpx.HTTPError:
            raise HTTPException(503, "Private storage is temporarily unavailable.")
        if result.status_code >= 400:
            raise HTTPException(503, "Private storage operation failed.")
        return result

    def put(self, key, data):
        if self.cfg.storage_provider == "supabase":
            self._remote("POST", key, data)
        else:
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            encrypted = Fernet(self.cfg.storage_encryption_key.encode()).encrypt(data)
            with path.open("xb") as file:
                file.write(encrypted)
            path.chmod(0o600)

    def get(self, key):
        if self.cfg.storage_provider == "supabase":
            return self._remote("GET", key).content
        return Fernet(self.cfg.storage_encryption_key.encode()).decrypt(self._path(key).read_bytes())

    def delete(self, key):
        if self.cfg.storage_provider == "supabase":
            self._remote("DELETE", key)
        else:
            self._path(key).unlink(missing_ok=True)

    def signed_url(self, key):
        if self.cfg.storage_provider != "supabase":
            return None
        cfg = self.cfg
        try:
            response = httpx.post(
                f"{cfg.supabase_url}/storage/v1/object/sign/{cfg.supabase_storage_bucket}/{key}",
                json={"expiresIn": 60},
                headers={
                    "apikey": cfg.supabase_service_role_key,
                    "Authorization": f"Bearer {cfg.supabase_service_role_key}",
                },
                timeout=15,
            )
            response.raise_for_status()
            return cfg.supabase_url + "/storage/v1" + response.json()["signedURL"]
        except (httpx.HTTPError, KeyError):
            raise HTTPException(503, "Could not create a temporary download URL.")


def verify_private_bucket():
    cfg = settings()
    try:
        response = httpx.get(
            f"{cfg.supabase_url}/storage/v1/bucket/{cfg.supabase_storage_bucket}",
            headers={
                "apikey": cfg.supabase_service_role_key,
                "Authorization": f"Bearer {cfg.supabase_service_role_key}",
            },
            timeout=15,
        )
        response.raise_for_status()
        if response.json().get("public") is not False:
            raise RuntimeError("Medical document bucket must be private")
    except (httpx.HTTPError, ValueError):
        raise RuntimeError("Could not verify private document storage") from None
