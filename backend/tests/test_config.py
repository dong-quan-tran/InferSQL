from app.core.config import get_settings


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.app_name == "InferSQL Backend"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "dev"