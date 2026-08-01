"""KrengJAI evaluation foundations."""

from .schemas import AXES, SchemaError, load_examples, validate_dataset, validate_example
from .scoring import preference_margin, summarize_dataset, weighted_score

__all__ = [
    "AXES",
    "SchemaError",
    "load_examples",
    "preference_margin",
    "summarize_dataset",
    "validate_dataset",
    "validate_example",
    "weighted_score",
]

__version__ = "0.1.0"

