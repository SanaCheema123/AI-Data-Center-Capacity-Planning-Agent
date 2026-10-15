from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Provider-neutral text generation interface.

    Providers never query the database themselves. They receive only grounded,
    pre-validated context assembled by the application service layer.
    """

    name: str

    @abstractmethod
    def generate_text(self, prompt: str, *, context: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError
