#!/usr/bin/env python3
"""
Similarity Calculation Utilities
從 opchat 改造，用於計算向量相似度
"""

import numpy as np
from typing import Union, List
import logging

logger = logging.getLogger(__name__)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算兩個向量的餘弦相似度

    Args:
        a: 向量 A
        b: 向量 B

    Returns:
        相似度分數 [0, 1]，1 表示完全相同
    """
    if a is None or b is None:
        return 0.0

    # 計算範數
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    # 餘弦相似度
    similarity = np.dot(a, b) / (norm_a * norm_b + 1e-9)

    # 限制在 [-1, 1] 範圍（避免數值誤差）
    similarity = float(np.clip(similarity, -1.0, 1.0))

    # 轉換到 [0, 1] 範圍
    return (similarity + 1.0) / 2.0


def batch_cosine_similarity(
    query_vector: np.ndarray, vectors_matrix: np.ndarray, top_k: int = None
) -> Union[np.ndarray, tuple]:
    """
    計算查詢向量與一組向量的餘弦相似度

    Args:
        query_vector: 查詢向量 (shape: [dimension])
        vectors_matrix: 向量矩陣 (shape: [n, dimension])
        top_k: 如果指定，返回 Top-K 最相似的索引和分數

    Returns:
        如果 top_k=None: 相似度陣列 (shape: [n])
        如果 top_k>0: (indices, similarities) tuple
    """
    # 正規化向量
    query_norm = query_vector / (np.linalg.norm(query_vector) + 1e-9)
    vectors_norm = vectors_matrix / (
        np.linalg.norm(vectors_matrix, axis=1, keepdims=True) + 1e-9
    )

    # 批次計算相似度
    similarities = np.dot(vectors_norm, query_norm)

    # 轉換到 [0, 1] 範圍
    similarities = (similarities + 1.0) / 2.0

    if top_k is not None:
        # 取 Top-K
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_similarities = similarities[top_indices]
        return top_indices, top_similarities

    return similarities


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算歐氏距離

    Args:
        a: 向量 A
        b: 向量 B

    Returns:
        歐氏距離（越小越相似）
    """
    if a is None or b is None:
        return float("inf")

    return float(np.linalg.norm(a - b))


def dot_product(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算點積相似度

    Args:
        a: 向量 A
        b: 向量 B

    Returns:
        點積值
    """
    if a is None or b is None:
        return 0.0

    return float(np.dot(a, b))


# 預計算範數（從 opchat 移植，用於加速）
def precompute_norms(embeddings_matrix: np.ndarray) -> np.ndarray:
    """
    預計算所有向量的範數

    Args:
        embeddings_matrix: 向量矩陣 (shape: [n, dimension])

    Returns:
        範數陣列 (shape: [n])
    """
    return np.linalg.norm(embeddings_matrix, axis=1)


def fast_cosine_similarity_with_norms(
    query_vector: np.ndarray,
    vectors_matrix: np.ndarray,
    precomputed_norms: np.ndarray,
) -> np.ndarray:
    """
    使用預計算範數的快速餘弦相似度計算

    Args:
        query_vector: 查詢向量
        vectors_matrix: 向量矩陣
        precomputed_norms: 預計算的範數

    Returns:
        相似度陣列
    """
    query_norm = np.linalg.norm(query_vector)
    if query_norm == 0:
        return np.zeros(len(vectors_matrix))

    # 點積
    dot_products = np.dot(vectors_matrix, query_vector)

    # 餘弦相似度
    similarities = dot_products / (precomputed_norms * query_norm + 1e-9)

    # 限制範圍
    similarities = np.clip(similarities, -1.0, 1.0)

    # 轉換到 [0, 1]
    return (similarities + 1.0) / 2.0


# 測試代碼
if __name__ == "__main__":
    # 測試向量
    vec_a = np.array([1.0, 0.0, 0.0])
    vec_b = np.array([0.0, 1.0, 0.0])
    vec_c = np.array([1.0, 0.0, 0.0])

    print("=== 相似度測試 ===")
    print(f"vec_a 與 vec_b (正交): {cosine_similarity(vec_a, vec_b):.4f}")
    print(f"vec_a 與 vec_c (相同): {cosine_similarity(vec_a, vec_c):.4f}")

    # 批次測試
    query = np.random.rand(128)
    matrix = np.random.rand(1000, 128)

    print("\n=== 批次相似度測試 ===")
    similarities = batch_cosine_similarity(query, matrix)
    print(f"相似度陣列 shape: {similarities.shape}")
    print(f"最高相似度: {similarities.max():.4f}")

    # Top-K 測試
    indices, top_sims = batch_cosine_similarity(query, matrix, top_k=5)
    print(f"\nTop-5 相似索引: {indices}")
    print(f"Top-5 相似度: {top_sims}")

    # 性能測試
    import time

    print("\n=== 性能測試 ===")

    # 標準方法
    start = time.time()
    for _ in range(100):
        _ = batch_cosine_similarity(query, matrix)
    elapsed = time.time() - start
    print(f"標準方法 (100 次): {elapsed:.4f} 秒")

    # 預計算範數方法
    norms = precompute_norms(matrix)
    start = time.time()
    for _ in range(100):
        _ = fast_cosine_similarity_with_norms(query, matrix, norms)
    elapsed = time.time() - start
    print(f"預計算範數方法 (100 次): {elapsed:.4f} 秒")
