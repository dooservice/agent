from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket

import msgspec
import tomlkit

from dooservice_models import DEFAULT_DATA_DIR
from dooservice_sdk import Config

TEMPLATES_DIR      = Path(__file__).parent / "templates"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "agent.toml"


def resolve_agent_id() -> str:
    return socket.gethostname()


class AgentConfig(msgspec.Struct, frozen=True):
    nats_url:               str = ""
    nats_user:              str = "agent"
    nats_password:          str = ""
    region:                 str = ""
    heartbeat_interval:     int = 30
    max_concurrent_backups: int = 3
    sdk: Config = msgspec.field(default_factory=Config)

    @classmethod
    def from_toml(cls, path: Path) -> AgentConfig:
        with open(path) as file:
            data = tomlkit.load(file).unwrap()
        return cls(
            nats_url=data.get("nats_url", ""),
            nats_user=data.get("nats_user", "agent"),
            nats_password=data.get("nats_password", ""),
            region=data.get("region", ""),
            heartbeat_interval=data.get("heartbeat_interval", 30),
            max_concurrent_backups=data.get("max_concurrent_backups", 3),
            sdk=Config.from_dict(data.get("sdk", {})),
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> AgentConfig:
        if config_path is not None:
            return cls.from_toml(config_path)
        env_override = os.environ.get("DOOSERVICE_AGENT_CONFIG")
        if env_override:
            return cls.from_toml(Path(env_override))
        if DEFAULT_CONFIG_PATH.exists():
            return cls.from_toml(DEFAULT_CONFIG_PATH)
        return cls.create_default()

    @classmethod
    def create_default(cls) -> AgentConfig:
        DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATES_DIR / "agent.toml", DEFAULT_CONFIG_PATH)
        return cls.from_toml(DEFAULT_CONFIG_PATH)
