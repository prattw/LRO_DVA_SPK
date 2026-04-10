"""Runtime settings for the API (environment variables + defaults)."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from vantage_preprocess.chunking.config import ChunkingConfig


class ApiSettings(BaseSettings):
    """API server defaults. See ``.env.example`` for variable names."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("VANTAGE_API_HOST"),
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("VANTAGE_API_PORT"),
    )
    api_reload: bool = Field(default=False, validation_alias=AliasChoices("VANTAGE_API_RELOAD"))
    log_level: str = Field(default="info", validation_alias=AliasChoices("VANTAGE_LOG_LEVEL"))
    data_dir: str = Field(
        default="./var/vantage",
        validation_alias=AliasChoices("VANTAGE_DATA_DIR"),
    )
    max_upload_bytes: int = Field(
        default=100 * 1024 * 1024,
        ge=1024,
        validation_alias=AliasChoices("VANTAGE_MAX_UPLOAD_BYTES"),
    )
    max_files_per_job: int = Field(
        default=50,
        ge=1,
        le=500,
        validation_alias=AliasChoices("VANTAGE_MAX_FILES_PER_JOB"),
    )
    chunk_min_words: int = Field(
        default=500,
        ge=50,
        validation_alias=AliasChoices("VANTAGE_CHUNK_MIN_WORDS"),
    )
    chunk_max_words: int = Field(
        default=2000,
        ge=100,
        validation_alias=AliasChoices("VANTAGE_CHUNK_MAX_WORDS"),
    )
    chunk_target_low: int = Field(
        default=1200,
        ge=50,
        validation_alias=AliasChoices("VANTAGE_CHUNK_TARGET_LOW"),
    )
    chunk_target_high: int = Field(
        default=1500,
        ge=50,
        validation_alias=AliasChoices("VANTAGE_CHUNK_TARGET_HIGH"),
    )
    chunk_overlap_low: int = Field(
        default=100,
        ge=0,
        validation_alias=AliasChoices("VANTAGE_CHUNK_OVERLAP_LOW"),
    )
    chunk_overlap_high: int = Field(
        default=200,
        ge=0,
        validation_alias=AliasChoices("VANTAGE_CHUNK_OVERLAP_HIGH"),
    )
    portal_txt_max_bytes: int = Field(
        default=9_437_184,
        ge=4096,
        description="Max UTF-8 bytes per portal .txt file (Army Vantage web upload).",
        validation_alias=AliasChoices("VANTAGE_PORTAL_TXT_MAX_BYTES"),
    )

    def chunking_model(self) -> ChunkingConfig:
        """Build chunking config from environment-backed fields."""
        return ChunkingConfig(
            min_words=self.chunk_min_words,
            max_words=self.chunk_max_words,
            target_words_low=self.chunk_target_low,
            target_words_high=self.chunk_target_high,
            overlap_words_low=self.chunk_overlap_low,
            overlap_words_high=self.chunk_overlap_high,
        )


def get_settings() -> ApiSettings:
    return ApiSettings()
