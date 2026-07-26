"""Built-in evaluated-system adapters."""

from finmirror.adapters.base import Adapter, run_adapter
from finmirror.adapters.baselines import (
    EvidenceProgramBaseline,
    MemorizedBaseline,
    OracleAdapter,
)

__all__ = [
    "Adapter",
    "EvidenceProgramBaseline",
    "MemorizedBaseline",
    "OracleAdapter",
    "run_adapter",
]
