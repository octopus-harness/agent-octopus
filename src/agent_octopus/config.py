import os
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_api_base: str = Field(
        default="http://100.95.26.48:1919/v1",
        alias="OLLAMA_API_BASE",
    )
    ollama_model: str = Field(
        default="Qwen3.6-35B-A3B-NVFP4",
        alias="OLLAMA_MODEL",
    )
    ollama_api_key: str = Field(
        default="ollama",
        alias="OLLAMA_API_KEY",
    )
    mcp_config_path: str = Field(
        default="mcp_config.json",
        alias="MCP_CONFIG_PATH",
    )
    com_bin: str = Field(
        default="com",
        alias="COM_BIN",
    )


class MCPServerDefinition(BaseModel):
    command: str = "node"
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class MCPConfigFile(BaseModel):
    mcpServers: dict[str, MCPServerDefinition] = Field(default_factory=dict)


def load_settings() -> Settings:
    return Settings()


def get_model(settings: Settings | None = None) -> OpenAIChatModel:
    if settings is None:
        settings = load_settings()
    provider = OpenAIProvider(
        base_url=settings.ollama_api_base,
        api_key=settings.ollama_api_key,
    )
    return OpenAIChatModel(
        model_name=settings.ollama_model,
        provider=provider,
    )
