from backend.providers.tracing import LocalTracer, init_tracing, start_span


def test_tracing_emits_span(capsys):
    tracer = LocalTracer(service_name="aegis-test", exporter="console")
    span = tracer.start_span("unit.test", component="pytest")
    span.set_attribute("ok", True)
    span.end("ok")
    tracer.export(span)
    captured = capsys.readouterr().out
    assert "unit.test" in captured
    assert "aegis-test" in captured
    assert span.duration_ms >= 0


def test_start_span_context_manager():
    init_tracing()  # ensure singleton path works
    with start_span("ctx.demo", path="tests") as span:
        span.set_attribute("step", 1)
    assert span.status == "ok"
    assert span.end_ns is not None
