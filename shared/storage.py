from io import BytesIO
from typing import BinaryIO

from minio import Minio

from shared.config import Settings, get_settings


def get_minio_client(settings: Settings | None = None) -> Minio:
    settings = settings or get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )


def put_json_object(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/json",
    settings: Settings | None = None,
) -> str:
    client = get_minio_client(settings)
    client.put_object(
        bucket,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return f"s3://{bucket}/{object_name}"


def put_stream(
    bucket: str,
    object_name: str,
    stream: BinaryIO,
    length: int,
    content_type: str = "application/octet-stream",
    settings: Settings | None = None,
) -> str:
    client = get_minio_client(settings)
    client.put_object(bucket, object_name, stream, length=length, content_type=content_type)
    return f"s3://{bucket}/{object_name}"
