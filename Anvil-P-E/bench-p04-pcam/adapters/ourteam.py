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
        self.params = model_params
        
    def predict_precision(self, corrupted_query: np.ndarray) -> np.ndarray:
        # Noise-Gated Precision: Give high precision to observed features,
        # and low precision to masked (zeroed) features.
        # Since the query has high masking (60-85%), this prevents noise
        # from pulling the dynamics away from the correct pattern.
        
        pi = np.where(np.abs(corrupted_query) > 1e-6, 5.0, 0.1)
        
        # Normalize
        pi = pi / np.mean(pi)
        
        # Clip
        return np.clip(pi, self.params.get("pi_min", 0.1), self.params.get("pi_max", 10.0))
