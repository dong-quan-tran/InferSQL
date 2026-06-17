import json
import logging

from app.core.logging import configure_logging, set_request_id, clear_request_id


def test_json_logging_smoke(capfd) -> None:
    # Configure JSON logging
    configure_logging(json_logs=True, log_level="INFO")

    logger = logging.getLogger("app.test")
    set_request_id("test-request-id")

    logger.info("json log message")

    clear_request_id()

    out, err = capfd.readouterr()
    assert err == ""

    # Should be valid JSON with our message and request_id
    payload = json.loads(out.strip())
    assert payload["message"] == "json log message"
    assert payload["request_id"] == "test-request-id"
    assert payload["logger"] == "app.test"
    assert payload["level"] == "INFO"


def test_plain_text_logging_smoke(capfd) -> None:
    # Configure plain-text logging (the path that used to explode)
    configure_logging(json_logs=False, log_level="INFO")

    logger = logging.getLogger("app.test.plain")
    set_request_id("plain-request")

    # Intentionally log without stage/dataset/error_code extras
    logger.info("plain text log message")

    clear_request_id()

    out, err = capfd.readouterr()
    assert err == ""

    # Basic sanity checks: message and logger name are present
    assert "plain text log message" in out
    assert "app.test.plain" in out
    assert "plain-request" in out