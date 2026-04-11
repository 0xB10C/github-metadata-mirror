"""Site configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Immutable site configuration, typically populated from CLI args."""

    title: str
    owner: str
    repository: str
    footer: str  # raw HTML allowed
    base_url: str  # e.g. "/" or "/mirror/" — always ends with /
    input_dir: Path
    output_dir: Path
    subset: bool = False

    def __post_init__(self) -> None:
        # Ensure base_url always ends with /
        if not self.base_url.endswith("/"):
            object.__setattr__(self, "base_url", self.base_url + "/")
