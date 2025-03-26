"""
Vector operations for matching functionality.

This module contains utility functions for working with vector embeddings.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


def average_vectors(vectors: list[list[float]]) -> list[float]:
    """
    Utility to compute the average vector from a list of vectors.

    Args:
        vectors: List of embedding vectors to average

    Returns:
        The averaged vector
    """
    if not vectors:
        raise ValueError("Cannot average an empty list of vectors")
    return np.mean(np.array(vectors), axis=0).tolist()
