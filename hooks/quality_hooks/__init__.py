"""Project-owned quality hook interface and default implementations."""

from .contracts import HookContext, HookResult, QualityHook
from .registry import default_registry

__all__ = ["HookContext", "HookResult", "QualityHook", "default_registry"]
