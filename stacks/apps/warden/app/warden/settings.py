from __future__ import annotations

from pydantic_settings import BaseSettings, EnvSettingsSource, InitSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict


class EnvironmentSettings(BaseSettings):
    """Use the container's environment snapshot without reading configuration files."""

    model_config = SettingsConfigDict(
        env_prefix="WARDEN_", extra="ignore", frozen=True, hide_input_in_errors=True,
    )

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], init_settings: InitSettingsSource,
        env_settings: EnvSettingsSource, dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        environment = init_settings.init_kwargs.pop("_environment", None)
        if environment is not None:
            env_settings.env_vars = {key.lower(): value for key, value in environment.items()}
        return init_settings, env_settings
