from __future__ import annotations

from typing import Protocol


class CapabilityAdapter(Protocol):
    name: str

    def describe(self) -> dict[str, object]:
        ...

    def validate(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> tuple[bool, list[str]]:
        ...

    def execute(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> dict[str, object]:
        ...

