"""FinMirror: paired counterfactual evaluation for financial AI."""

from finmirror.evaluator import evaluate
from finmirror.models import BenchmarkCase, CalculationOperand, Document, Prediction

__all__ = [
    "BenchmarkCase",
    "CalculationOperand",
    "Document",
    "Prediction",
    "evaluate",
]
__version__ = "0.1.1"
