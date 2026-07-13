from typing import Any, Dict, List, Optional

class MemoryProvider:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def store(self, key: str, value: Any, **kwargs: Any) -> None:
        pass

    def retrieve(self, key: str, **kwargs: Any) -> Optional[Any]:
        return None
        
    def delete(self, key: str, **kwargs: Any) -> None:
        pass
