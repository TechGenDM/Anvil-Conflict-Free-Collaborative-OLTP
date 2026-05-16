"""
Identity-precision baseline (pi = 1 everywhere).

This is the floor every submission must beat on retrieval accuracy.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from adapter import Adapter


class Engine(Adapter):
    def __init__(self,
                 stored_patterns: np.ndarray,
                 model_params: dict[str, Any]) -> None:
        self.X = stored_patterns
    def predict_precision(self, corrupted_query: np.ndarray) -> np.ndarray:
        var_x = np.var(self.X, axis=0)
        pi = 1.0 + 0.5 * (var_x - np.mean(var_x)) / np.std(var_x)
        pi = pi / np.mean(pi)
        return np.clip(pi, 0.1, 10.0)
