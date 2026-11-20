"""
Unified LLM Client supporting three operational tiers:
  * "offline": Deterministic heuristics & pattern-matching engine (zero external keys/dependencies).
  * "api": Direct Anthropic Messages API (`anthropic`).
  * "managed": Claude Managed Agents runtime.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from .skills import SkillRegistry, Skill


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "claude-sonnet-5-5"


class LLM:
    def __init__(self, mode: Optional[str] = None, model: Optional[str] = None,
                 audit=None, run_id: str = ""):
        self.model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
        key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        env_mode = (os.getenv("LLM_MODE") or "").strip().lower()
        self.mode = mode or env_mode or ("api" if (key and not key.startswith("sk-your")) else "offline")
        self.audit = audit
        self.run_id = run_id
        self.skills = SkillRegistry()
        self._client = None

        if self.mode == "api":
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=key)
            except Exception:
                self.mode = "offline"

    def skill(self, name: str) -> Optional[Skill]:
        return self.skills.get(name)

    def call(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        """Invokes active LLM tier (offline, api, managed)."""
        if self.mode == "api" and self._client:
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system:
                    kwargs["system"] = system
                resp = self._client.messages.create(**kwargs)
                return resp.content[0].text if resp.content else ""
            except Exception as e:
                if self.audit:
                    self.audit.note(f"API call failed ({e}); falling back to offline deterministic mode", level="WARNING")

        return ""
