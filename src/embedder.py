"""Embedder abstraction supporting Gemini embeddings and Local multilingual-e5 embeddings."""

from abc import ABC, abstractmethod
from typing import List
import numpy as np


class Embedder(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generates embedding vectors for a list of texts."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """Generates an embedding vector for a single query."""
        pass


class GeminiEmbedder(Embedder):
    def __init__(self, model_name: str = "gemini-embedding-001", api_key: str = None):
        import os
        from google import genai
        
        self.key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.client = genai.Client(api_key=self.key) if self.key else None

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not configured for GeminiEmbedder.")
        
        vectors = []
        for text in texts:
            resp = self.client.models.embed_content(
                model=self.model_name,
                contents=text
            )
            vectors.append(resp.embeddings[0].values)
        return np.array(vectors, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not configured for GeminiEmbedder.")
        resp = self.client.models.embed_content(
            model=self.model_name,
            contents=query
        )
        return np.array(resp.embeddings[0].values, dtype=np.float32)


class LocalEmbedder(Embedder):
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        # e5 models expect "passage: " prefix for documents
        prefixed = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(prefixed, normalize_embeddings=True)
        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        # e5 models expect "query: " prefix for retrieval queries
        prefixed = f"query: {query}"
        embedding = self.model.encode(prefixed, normalize_embeddings=True)
        return np.array(embedding, dtype=np.float32)
