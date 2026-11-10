import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


db_instance = Database()


async def connect_to_mongo():
    """Establish async MongoDB connection pool."""
    logger.info("Connecting to MongoDB...")
    try:
        db_instance.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            maxIdleTimeMS=settings.MONGODB_MAX_IDLE_TIME_MS,
            serverSelectionTimeoutMS=5000,
        )
        db_instance.db = db_instance.client[settings.MONGODB_DB_NAME]
        logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e


async def close_mongo_connection():
    """Gracefully close MongoDB connection pool."""
    logger.info("Closing MongoDB connection...")
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Dependency to retrieve active MongoDB database instance."""
    if db_instance.db is None:
        raise RuntimeError("Database is not initialized. Ensure connect_to_mongo() was called.")
    return db_instance.db
