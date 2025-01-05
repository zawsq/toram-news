# ruff: noqa: ARG003
import logging
import sys
from pathlib import Path
from typing import Annotated

from pydantic import ValidationError
from pydantic.networks import UrlConstraints
from pydantic_core import MultiHostUrl
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings.sources import SettingsError

MongoSRVDsn = Annotated[MultiHostUrl, UrlConstraints(allowed_schemes=["mongodb+srv"])]
BASE_PATH = Path(__file__).parent.parent


class Config(BaseSettings):
    """A general configuration setup to read either .env or environment keys."""

    # http connection
    PORT: int = 8080
    HOSTNAME: str = "0.0.0.0"  # noqa: S104
    HTTP_SERVER: bool = False

    # database connection
    MONGO_DB_URL: MongoSRVDsn
    MONGO_DB_NAME: str = "toram"

    # discord connection
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(
        env_file=f"{BASE_PATH}/.env",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            DotEnvSettingsSource(settings_cls),
            EnvSettingsSource(settings_cls),
        )


try:
    config = Config()  # pyright: ignore[reportCallIssue]
except (ValidationError, SettingsError):
    logging.exception("Configuration Error")
    sys.exit(1)
