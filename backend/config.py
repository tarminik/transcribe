from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def varenv(varname):
    return Field(default=..., validation_alias=AliasChoices(varname))


class EnvConf(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


class AssemblyAI(EnvConf):
    api_key: str = varenv("ASSEMBLYAI_API_KEY")


class EnvironmentSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    assemblyai: AssemblyAI

    def __init__(self, **data: Any):
        super().__init__(
            assemblyai=AssemblyAI(),
            **data,
        )


env_settings = EnvironmentSettings()
