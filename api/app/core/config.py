from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: Literal["local", "dev", "prod"] = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
