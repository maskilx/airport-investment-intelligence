"""Backward-compatible entry point. The runtime lives in `airport_agent.runtime`; backends in `airport_agent.models`."""
from .models import AnthropicBackend, ModelBackend, ScriptedBackend  # noqa: F401
from .runtime import SYSTEM_PROMPT, Agent, TurnResult  # noqa: F401
