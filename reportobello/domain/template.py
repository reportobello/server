from dataclasses import dataclass


@dataclass(kw_only=True)
class Template:
    name: str
    template: str
    version: int
