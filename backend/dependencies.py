"""Application configuration loaded from the local environment."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings that should stay outside source control."""

    odds_api_key: str | None = Field(default=None, validation_alias="THE_ODDS_API_KEY")
    # API-Sports sells NFL and NBA coverage separately. A shared key is also
    # supported for accounts where both products are enabled on one key.
    api_sports_key: str | None = Field(default=None, validation_alias="API_SPORTS_KEY")
    api_sports_nfl_key: str | None = Field(default=None, validation_alias="API_SPORTS_NFL_KEY")
    api_sports_nba_key: str | None = Field(default=None, validation_alias="API_SPORTS_NBA_KEY")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
