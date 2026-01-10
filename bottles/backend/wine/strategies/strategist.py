# strategist.py
#
# Base classes for execution strategies.

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Dict, List, Any


@dataclass
class ExecutionContext:
    """
    State container for the execution pipeline.
    Accumulates environment variables and build the command parts.
    """

    env: Dict[str, str] = field(default_factory=dict)
    # The command being built. Usually starts with the runner or umu-run.
    command_parts: List[str] = field(default_factory=list)
    # Metadata used by strategies
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Flags for clean/steam environment requests
    return_steam_env: bool = False
    return_clean_env: bool = False
    is_terminal: bool = False
    is_minimal: bool = False

    def add_env(self, key: str, value: str):
        self.env[key] = value

    def concat_env(self, key: str, value: str, sep: str = ":"):
        if key in self.env and self.env[key]:
            self.env[key] = f"{self.env[key]}{sep}{value}"
        else:
            self.env[key] = value

    def wrap_command(self, wrapper: str):
        """Prefix the command parts with a wrapper."""
        self.command_parts.insert(0, wrapper)

    def append_args(self, args: str):
        """Append arguments to the command."""
        if args:
            self.command_parts.append(args)


class ExecutionStrategist(ABC):
    """
    Base class for specific execution logic (Graphics, Sync, etc.)
    """

    @abstractmethod
    def apply(self, context: ExecutionContext, config: Any):
        """
        Modify the context based on bottle configuration.
        """
