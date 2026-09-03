from app.core.config import Settings


def test_railway_database_url_uses_installed_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@postgres:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:password@postgres:5432/app"


def test_explicit_database_driver_is_preserved() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:password@postgres:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:password@postgres:5432/app"
