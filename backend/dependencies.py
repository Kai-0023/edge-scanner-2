"""Application configuration loaded from the local environment."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings that should stay outside source control."""

    odds_api_key: str | None = Field(default=None, validation_alias="THE_ODDS_API_KEY")
    # API-Sports sells NFL and NBA coverage separately. A shared key is also
    # supported for accounts where both products are enabled on one key.
    api_sports_key: str | None = Field(default=None, validation_alias="API_SPORTS_KEY")
    api_sports_nfl_key: str | None = Field(default=None, validation_alias="API_SPORTS_NFL_KEY")
    api_sports_nba_key: str | None = Field(default=None, validation_alias="API_SPORTS_NBA_KEY")
    # Google AI Studio keys have been named differently across the dashboard
    # and examples, so accept the common local names without copying a secret
    # into the client or source control.
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"),
    )
    gemini_model: str = Field(default="gemini-3.8-flash", validation_alias="GEMINI_MODEL")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("gemini_model", mode="before")
    @classmethod
    def use_default_gemini_model_when_blank(cls, value: object) -> str:
        """An empty optional .env line should retain the safe default model."""

        return "gemini-3.8-flash" if value is None or not str(value).strip() else str(value).strip()


settings = Settings()
