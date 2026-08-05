import secrets
import warnings
from typing import Annotated, Any, Literal, Self
from urllib.parse import quote

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    Field,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import get_env_file


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    # SECRET_KEY is retained only so legacy deployments can be rotated away;
    # new access and password tokens never use it.
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_SECRET_KEY: str = secrets.token_urlsafe(32)
    PASSWORD_TOKEN_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ISSUER: str = "full-stack-fastapi-template"
    JWT_AUDIENCE: str = "full-stack-fastapi-template"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    OBSERVABILITY_HTTP_SLOW_THRESHOLD_MS: int = 1000

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    CACHE_REDIS_CONNECT_TIMEOUT_SECONDS: float = Field(default=0.2, gt=0)
    CACHE_REDIS_SOCKET_TIMEOUT_SECONDS: float = Field(default=0.2, gt=0)
    CELERY_VISIBILITY_TIMEOUT_SECONDS: int = Field(default=3600, gt=0)
    CELERY_RESULT_EXPIRES_SECONDS: int = Field(default=900, gt=0)

    @property
    def celery_broker_url(self) -> str:
        return self._redis_url(database=0)

    @property
    def celery_result_backend_url(self) -> str:
        return self._redis_url(database=1)

    @property
    def redis_cache_url(self) -> str:
        return self._redis_url(database=2)

    def _redis_url(self, *, database: int) -> str:
        credentials = (
            f":{quote(self.REDIS_PASSWORD, safe='')}@" if self.REDIS_PASSWORD else ""
        )
        return f"redis://{credentials}{self.REDIS_HOST}:{self.REDIS_PORT}/{database}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "514756264@qq.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        if self.ENVIRONMENT == "production" and not self.REDIS_PASSWORD:
            raise ValueError("REDIS_PASSWORD must be configured in production")
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret(
            "ACCESS_TOKEN_SECRET_KEY", self.ACCESS_TOKEN_SECRET_KEY
        )
        self._check_default_secret(
            "PASSWORD_TOKEN_SECRET_KEY", self.PASSWORD_TOKEN_SECRET_KEY
        )
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret("REDIS_PASSWORD", self.REDIS_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self

    @model_validator(mode="after")
    def _validate_observability_settings(self) -> Self:
        if self.OBSERVABILITY_HTTP_SLOW_THRESHOLD_MS <= 0:
            raise ValueError("OBSERVABILITY_HTTP_SLOW_THRESHOLD_MS must be positive")
        return self


settings = Settings()  # type: ignore
