#!/usr/bin/env python3
"""
Embedding Engine for Scope 3 Estimation System
改造自 foodLCA 與 USEEIO，支援本地端 embedding
"""

from typing import List, Union
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    本地端 Embedding 引擎
    使用 sentence-transformers 實現多語言語意向量化
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        device: str = "auto",
        cache_folder: str = None,
    ):
        """
        初始化 Embedding 引擎

        Args:
            model_name: sentence-transformers 模型名稱
            device: 'cpu', 'cuda', 或 'auto' (自動檢測)
            cache_folder: 模型快取目錄
        """
        self.model_name = model_name

        # 自動檢測設備
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"🚀 初始化 Embedding 引擎")
        logger.info(f"   模型: {model_name}")
        logger.info(f"   設備: {self.device}")

        if self.device == "cuda":
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
            logger.info(
                f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB"
            )

        # 載入模型
        try:
            self.model = SentenceTransformer(
                model_name, device=self.device, cache_folder=cache_folder
            )
            logger.info("✅ 模型載入成功")
        except Exception as e:
            logger.error(f"❌ 模型載入失敗: {e}")
            raise

        # 取得 embedding 維度
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"   Embedding 維度: {self.dimension}")

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        convert_to_numpy: bool = True,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        將文本編碼為向量

        Args:
            texts: 單個文本或文本列表
            batch_size: 批次大小
            show_progress: 是否顯示進度條
            convert_to_numpy: 是否轉換為 NumPy 陣列
            normalize: 是否正規化向量（用於餘弦相似度）

        Returns:
            向量陣列 (shape: [n, dimension])
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=convert_to_numpy,
                normalize_embeddings=normalize,
            )
            return embeddings
        except Exception as e:
            logger.error(f"❌ Embedding 編碼失敗: {e}")
            raise

    def encode_single(self, text: str) -> np.ndarray:
        """編碼單個文本（便利函數）"""
        return self.encode(text, show_progress=False)[0]

    def get_dimension(self) -> int:
        """取得 embedding 維度"""
        return self.dimension

    def to(self, device: str):
        """切換設備"""
        self.device = device
        self.model.to(device)
        logger.info(f"🔄 切換到設備: {device}")
        return self


# GPU/CPU 檢查工具（從 USEEIO 改造）
def check_gpu() -> dict:
    """
    檢查 GPU 狀態並返回詳細資訊

    Returns:
        GPU 資訊字典
    """
    try:
        torch.cuda.init()
        cuda_available = torch.cuda.is_available()
    except Exception as e:
        logger.error(f"CUDA 初始化錯誤: {e}")
        cuda_available = False

    gpu_info = {
        "cuda_available": cuda_available,
        "device_count": torch.cuda.device_count() if cuda_available else 0,
        "current_device": None,
        "device_name": None,
        "memory_total_mb": None,
        "memory_allocated_mb": None,
        "cuda_version": torch.version.cuda if hasattr(torch.version, "cuda") else None,
    }

    if gpu_info["cuda_available"]:
        gpu_info["current_device"] = torch.cuda.current_device()
        gpu_info["device_name"] = torch.cuda.get_device_name(0)
        gpu_info["memory_total_mb"] = (
            torch.cuda.get_device_properties(0).total_memory / 1024**2
        )
        gpu_info["memory_allocated_mb"] = torch.cuda.memory_allocated(0) / 1024**2

    return gpu_info


# 測試代碼
if __name__ == "__main__":
    # 檢查 GPU
    gpu_info = check_gpu()
    print("=== GPU 資訊 ===")
    for key, value in gpu_info.items():
        print(f"{key}: {value}")

    # 測試 Embedding
    print("\n=== Embedding 測試 ===")
    engine = EmbeddingEngine()

    # 測試文本
    texts = ["購買筆記型電腦", "Laptop Computer", "電力消耗 1000 度"]

    embeddings = engine.encode(texts, show_progress=True)
    print(f"編碼結果 shape: {embeddings.shape}")
    print(f"第一個向量前 5 個維度: {embeddings[0][:5]}")

    # 計算相似度
    from sklearn.metrics.pairwise import cosine_similarity

    sim_matrix = cosine_similarity(embeddings)
    print(f"\n相似度矩陣:")
    print(sim_matrix)
    print(f"\n「購買筆記型電腦」與「Laptop Computer」的相似度: {sim_matrix[0, 1]:.4f}")
