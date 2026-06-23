import json
import logging

from app.core.logging import configure_logging, set_request_id, clear_request_id

from fastapi.testclient import TestClient

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


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_query_execute_logging_includes_structured_fields(
    client: TestClient,
) -> None:
    configure_logging(json_logs=False, log_level="INFO")

    handler = _ListHandler()
    logger = logging.getLogger("app.services.query_service")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        response = client.post(
            "/query/execute",
            json={"sql": "SELECT symbol, close FROM prices LIMIT 1"},
        )
        assert response.status_code == 200

        matching = [r for r in handler.records if r.msg == "query executed"]
        assert matching, "expected a 'query executed' log record"

        record = matching[-1]

        assert getattr(record, "stage", None) == "execute"
        assert isinstance(getattr(record, "total_ms", None), (int, float))
        assert getattr(record, "engine", None) == "datafusion"
        assert getattr(record, "dataset", None) == "prices"

        sql_hash = getattr(record, "sql_hash", None)
        assert isinstance(sql_hash, str)
        assert sql_hash != ""
    finally:
        logger.removeHandler(handler)