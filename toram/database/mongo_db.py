import dns.resolver
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConfigurationError

from toram.config import config


class MongoDB:
    """
    A MongoDB database connection.

    Parameters:
        name (str | None): The name of the database to connect to. Defaults to config.MONGO_DB_NAME.
    """

    def __init__(self, name: str | None = None) -> None:
        """
        Initializes the MongoDB connection.

        Raises:
            ConfigurationError: If the MongoDB connection configuration is invalid.
        """
        try:
            self.client = AsyncIOMotorClient(host=str(config.MONGO_DB_URL))
        except ConfigurationError:
            dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
            dns.resolver.default_resolver.nameservers = ["8.8.8.8"]
            self.client = AsyncIOMotorClient(host=str(config.MONGO_DB_URL))
        self.db = self.client[name if name else config.MONGO_DB_NAME]

    async def update_news_id(self, news_id: str) -> bool:
        """
        Update or add latest news id to database.

        Parameters:
            news_id (int): The ID of the news.

        Returns:
            bool: Whether the news id was added successfully.
        """
        collection = self.db["toram_news"]
        result = await collection.update_one(
            filter={"_id": "news_id"},
            update={"$set": {"last_news": news_id}},
            upsert=True,
        )
        return result.acknowledged

    async def fetch_last_news(self) -> int | None:
        """
        Fetch the last news ID from the database.

        Returns:
            int | None: The ID of the last news if it exists, otherwise None.
        """
        collection = self.db["toram_news"]
        document = await collection.find_one({"_id": "news_id"})

        return document.get("last_news") if document else None
