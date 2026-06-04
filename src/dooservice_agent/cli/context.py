from __future__ import annotations

from dooservice_sdk import DooServiceSDK

from ..config import AgentConfig


def open_sdk() -> DooServiceSDK:
    return DooServiceSDK(AgentConfig.load().sdk)
