from app.worker.handler import handler


def test_handler_returns_ok_for_empty_event() -> None:
    assert handler({}, object()) == {"status": "ok"}


def test_handler_returns_ok_with_records() -> None:
    event = {"Records": [{"body": "test"}]}
    assert handler(event, object()) == {"status": "ok"}
