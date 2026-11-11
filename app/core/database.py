import asyncio
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_mock: bool = False


db_instance = Database()


async def connect_to_mongo():
    """Establish async MongoDB connection pool with resilient in-memory fallback for local development."""
    logger.info("Connecting to MongoDB...")
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            maxIdleTimeMS=settings.MONGODB_MAX_IDLE_TIME_MS,
            serverSelectionTimeoutMS=2000,
        )
        # Actively test connection with timeout
        await asyncio.wait_for(client.admin.command("ping"), timeout=2.0)
        db_instance.client = client
        db_instance.db = client[settings.MONGODB_DB_NAME]
        db_instance.is_mock = False
        logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
    except Exception as e:
        if settings.APP_ENV in ["development", "dev", "test"] or settings.MONGODB_FALLBACK_TO_MEMORY:
            logger.warning(
                f"\n{'='*78}\n"
                f"⚠️  NOTICE: Could not connect to MongoDB at {settings.MONGODB_URL}\n"
                f"   Reason: {e}\n"
                f"   ⚡ Seamlessly activating in-memory MongoDB database (mongomock-motor)\n"
                f"   All authentication, catalog, orders, and dashboard features are active!\n"
                f"{'='*78}\n"
            )
            from mongomock_motor import AsyncMongoMockClient

            mock_client = AsyncMongoMockClient()
            db_instance.client = mock_client
            db_instance.db = mock_client[settings.MONGODB_DB_NAME]
            db_instance.is_mock = True
        else:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise e


async def close_mongo_connection():
    """Gracefully close MongoDB connection pool."""
    logger.info("Closing MongoDB connection...")
    if db_instance.client and not getattr(db_instance, "is_mock", False):
        db_instance.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Dependency to retrieve active MongoDB database instance."""
    if db_instance.db is None:
        raise RuntimeError("Database is not initialized. Ensure connect_to_mongo() was called.")
    return db_instance.db

