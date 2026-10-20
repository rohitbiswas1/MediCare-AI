"""Private service integration contract; the patient workflow deliberately does not call research inference."""

from typing import Literal
import httpx
from pydantic import BaseModel, Field, ConfigDict
from fastapi import HTTPException
from .config import settings


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    probability: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    identified: bool


class ResearchResult(BaseModel):
    status: Literal["experimental"]
    clinical_use: Literal[False]
    model_version: str
    predictions: list[Prediction]
    quality: dict
    uncertainty: str
    summary: str


def research_inference(
    modality: Literal["ecg", "xray"], data: bytes, filename: str, service_key: str, view=None
):
    cfg = settings()
    if cfg.production or not cfg.inference_url:
        raise HTTPException(503, "Clinical inference is disabled. No configured research service.")
    try:
        response = httpx.post(
            f"{cfg.inference_url.rstrip('/')}/{modality}",
            headers={"X-Service-Key": service_key},
            files={"file": (filename, data)},
            data={"view": view} if view else {},
            timeout=60,
        )
        response.raise_for_status()
        return ResearchResult.model_validate(response.json())
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Inference is unavailable or returned an invalid response.")
