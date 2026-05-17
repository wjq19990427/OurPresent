import logging
import os
from contextlib import asynccontextmanager

import aioboto3
import asyncpg
from fastapi import FastAPI

LOGGER = logging.getLogger("ourpresent.server")
APP_VERSION = "0.1.0"
DEFAULT_DATABASE_URL = "postgresql://ourpresent:ourpresent@db:5432/ourpresent"
DEFAULT_OBJECT_STORE_ENDPOINT = "http://minio:9000"
DEFAULT_OBJECT_STORE_ACCESS_KEY = "minioadmin"
DEFAULT_OBJECT_STORE_SECRET_KEY = "minioadmin"


def _database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _object_store_endpoint() -> str:
    return os.getenv("OBJECT_STORE_ENDPOINT", DEFAULT_OBJECT_STORE_ENDPOINT)


def _object_store_access_key() -> str:
    return os.getenv("OBJECT_STORE_ACCESS_KEY", DEFAULT_OBJECT_STORE_ACCESS_KEY)


def _object_store_secret_key() -> str:
    return os.getenv("OBJECT_STORE_SECRET_KEY", DEFAULT_OBJECT_STORE_SECRET_KEY)


async def _check_database() -> None:
    try:
        connection = await asyncpg.connect(_database_url())
    except Exception as exc:  # pragma: no cover - startup observability path
        LOGGER.warning("Database connectivity check failed: %s", exc)
        return

    try:
        await connection.execute("SELECT 1")
        LOGGER.info("Database connectivity check succeeded.")
    finally:
        await connection.close()


async def _check_object_store() -> None:
    session = aioboto3.Session()
    try:
        async with session.client(
            "s3",
            endpoint_url=_object_store_endpoint(),
            aws_access_key_id=_object_store_access_key(),
            aws_secret_access_key=_object_store_secret_key(),
            region_name="us-east-1",
        ) as client:
            await client.list_buckets()
            LOGGER.info("Object store connectivity check succeeded.")
    except Exception as exc:  # pragma: no cover - startup observability path
        LOGGER.warning("Object store connectivity check failed: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO)
    await _check_database()
    await _check_object_store()
    yield


app = FastAPI(title="OurPresent API", version=APP_VERSION, lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}
