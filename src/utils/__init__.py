"""
Utility modules for Scope 3 Estimator
"""

from .embedding import EmbeddingEngine
from .similarity import (
    cosine_similarity,
    batch_cosine_similarity,
    fast_cosine_similarity_with_norms,
    precompute_norms
)

__all__ = [
    'EmbeddingEngine',
    'cosine_similarity',
    'batch_cosine_similarity',
    'fast_cosine_similarity_with_norms',
    'precompute_norms'
]
