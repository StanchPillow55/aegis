from backend.providers.tracing import traced_span, capture_exception_with_context


def test_tracing_spans():
    # Test that decorators execute the function correctly even if tracing is unconfigured/no-op

    @traced_span("test_span", key="value")
    def my_func():
        return "ok"

    assert my_func() == "ok"


def test_capture_exception():
    try:
        raise ValueError("test error")
    except Exception as e:
        capture_exception_with_context(e, extra="info")
        # Just asserts it doesn't crash
        assert True
