"""Registry for project-owned quality hook implementations."""

from __future__ import annotations

from .backend import BackendQualityHook
from .contracts import HookContext, HookResult, QualityHook
from .frontend import FrontendComponentHook


class HookRegistry:
    def __init__(self, hooks: tuple[QualityHook, ...]) -> None:
        self._hooks = {hook.name: hook for hook in hooks}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._hooks)

    def run(self, context: HookContext, selected: tuple[str, ...] = ()) -> tuple[HookResult, ...]:
        names = selected or self.names
        unknown = tuple(name for name in names if name not in self._hooks)
        if unknown:
            raise ValueError(f"Unknown hook(s): {', '.join(unknown)}")
        return tuple(self._hooks[name].run(context) for name in names)


def default_registry() -> HookRegistry:
    return HookRegistry((BackendQualityHook(), FrontendComponentHook()))
