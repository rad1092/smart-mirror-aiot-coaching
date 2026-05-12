from __future__ import annotations

from typing import Any


class TriggerEngine:
    def should_call_llm(
        self,
        mode: str,
        event: str,
        features: Any | None = None,
        baseline_diff: dict[str, Any] | None = None,
    ) -> bool:
        del features, baseline_diff
        if mode == "exercise" and event == "session_completed":
            return True
        return False
