from src.core.monitoring.error_handler import ConfigError, ErrorHandler, RecoverableError


def test_error_handler_classifies_recoverable():
    handler = ErrorHandler(max_retries=2, retry_delay_seconds=1)
    classification = handler.handle(RecoverableError("retry"), "unit-test")
    assert classification == "recoverable"


def test_error_handler_classifies_fatal():
    handler = ErrorHandler(max_retries=2, retry_delay_seconds=1)
    classification = handler.handle(ConfigError("bad config"), "unit-test")
    assert classification == "fatal"
