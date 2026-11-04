"""Cloudflare R2 object storage (S3-compatible). Media for questions, diagrams, uploads."""

from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.config import Config

from app.config.settings import settings


@lru_cache
def get_r2():
    if not settings.r2_configured:
        raise RuntimeError("R2 is not configured — fill the R2_* values in .env")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3},
            connect_timeout=5,
            read_timeout=30,
        ),
    )


def upload(key: str, body: bytes | BinaryIO, content_type: str | None = None) -> str:
    extra = {"ContentType": content_type} if content_type else {}
    get_r2().put_object(Bucket=settings.r2_bucket_name, Key=key, Body=body, **extra)
    return key


def presigned_upload_url(key: str, content_type: str, expires: int = 600) -> str:
    """Browser uploads straight to R2 with this URL; the API never proxies the bytes."""
    return get_r2().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def presigned_download_url(key: str, expires: int = 3600) -> str:
    return get_r2().generate_presigned_url(
        "get_object", Params={"Bucket": settings.r2_bucket_name, "Key": key}, ExpiresIn=expires
    )


def delete(key: str) -> None:
    get_r2().delete_object(Bucket=settings.r2_bucket_name, Key=key)


def public_url(key: str) -> str | None:
    base = settings.r2_public_url.rstrip("/")
    return f"{base}/{key}" if base else None


def check() -> None:
    """Raises if the bucket is unreachable or credentials are wrong."""
    get_r2().head_bucket(Bucket=settings.r2_bucket_name)
