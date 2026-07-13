from typing import Any, Dict, Optional

class TracingProvider:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def start_span(self, name: str, **kwargs: Any) -> Any:
        return None

    def end_span(self, span: Any, **kwargs: Any) -> None:
        pass

    def log_event(self, event_name: str, **kwargs: Any) -> None:
        pass
