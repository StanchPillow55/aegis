from typing import Any, Dict, List, Optional

class LLMProvider:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return ""
        
    async def generate_async(self, prompt: str, **kwargs: Any) -> str:
        return ""
