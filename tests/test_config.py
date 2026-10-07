from app.config import Settings


def test_settings_reads_database_and_webhook_secret() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@db:5432/kvitto",
        webhook_secret="test-secret",
    )

    assert settings.database_url.endswith("/kvitto")
    assert settings.webhook_secret == "test-secret"
