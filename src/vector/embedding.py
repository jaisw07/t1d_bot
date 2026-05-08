from typing import List
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import numpy as np


class E5Embedder:
    """
    multilingual-e5-large embedder
    as specified in project methodology.
    """

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-large",
        batch_size: int = 16,
    ):

        self.model_name = model_name
        self.batch_size = batch_size

        print(f"[INFO] Loading embedding model: {model_name}")

        self.model = SentenceTransformer(model_name)

        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        print(f"[INFO] Embedding dimension: {self.embedding_dim}")

    # =====================================================
    # E5 formatting
    # =====================================================

    @staticmethod
    def format_passage(text: str) -> str:
        return f"passage: {text}"

    @staticmethod
    def format_query(text: str) -> str:
        return f"query: {text}"

    # =====================================================
    # Passage embeddings
    # =====================================================

    def embed_passages(
        self,
        texts: List[str],
        normalize: bool = True,
    ) -> np.ndarray:

        formatted = [
            self.format_passage(t)
            for t in texts
        ]

        embeddings = self.model.encode(
            formatted,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )

        return embeddings

    # =====================================================
    # Query embeddings
    # =====================================================

    def embed_query(
        self,
        text: str,
        normalize: bool = True,
    ) -> np.ndarray:

        formatted = self.format_query(text)

        embedding = self.model.encode(
            [formatted],
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )

        return embedding[0]