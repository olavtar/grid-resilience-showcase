# This project was developed with assistance from AI tools.

"""Shared Pydantic settings base pattern for all grid services."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Kafka connection settings shared across services."""

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: str | None = None
    kafka_sasl_username: str | None = None
    kafka_sasl_password: str | None = None
    kafka_consumer_group_id: str = "grid-default"

    model_config = {"env_prefix": ""}


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings."""

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "gridops"
    db_user: str = "gridops"
    db_password: str = "gridops"
    db_sslmode: str = "prefer"

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?sslmode={self.db_sslmode}"
        )

    model_config = {"env_prefix": ""}


class OtelSettings(BaseSettings):
    """OpenTelemetry exporter settings."""

    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "grid-service"

    model_config = {"env_prefix": ""}


class ServiceSettings(KafkaSettings, DatabaseSettings, OtelSettings):
    """Combined settings base for grid services."""

    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_prefix": ""}
