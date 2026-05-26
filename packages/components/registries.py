from __future__ import annotations

from packages.components.collectors.git import GitCollector
from packages.core.registry import SimpleRegistry


collector_registry = SimpleRegistry[type[GitCollector]]()
collector_registry.register(GitCollector.name, GitCollector)

