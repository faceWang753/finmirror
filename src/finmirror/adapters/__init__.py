"""Built-in evaluated-system adapters."""

from finmirror.adapters.base import Adapter, run_adapter
from finmirror.adapters.baselines import (
    EvidenceProgramBaseline,
    MemorizedBaseline,
    OracleAdapter,
)
from finmirror.adapters.openai_compatible import OpenAICompatibleAdapter

__all__ = [
    "Adapter",
    "EvidenceProgramBaseline",
    "MemorizedBaseline",
    "OpenAICompatibleAdapter",
    "OracleAdapter",
    "run_adapter",
]
