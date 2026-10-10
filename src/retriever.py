"""Hybrid Retriever combining Dense Cosine Similarity, BM25, and Reciprocal Rank Fusion."""

import re
from typing import List, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from src.models import KBChunk, RetrievalResult
from src.embedder import Embedder


def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class HybridRetriever:
    def __init__(self, chunks: List[KBChunk], embedder: Embedder, rrf_k: int = 60):
        self.chunks = chunks
        self.embedder = embedder
        self.rrf_k = rrf_k
        
        # 1. Initialize BM25
        corpus = [chunk.content for chunk in chunks]
        tokenized_corpus = [tokenize(doc) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # 2. Load or Compute Dense Embeddings using ChromaDB Persistence
        import chromadb
        client = chromadb.PersistentClient(path="chroma_db")
        self.collection = client.get_or_create_collection(name="pw_triage_kb")
        
        # Check which chunks are already in Chroma
        existing = self.collection.get(include=[])
        existing_ids = set(existing["ids"])
        
        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
        if new_chunks:
            print(f"Computing embeddings for {len(new_chunks)} new chunks...")
            new_corpus = [c.content for c in new_chunks]
            new_embeddings = self.embedder.embed_texts(new_corpus)
            
            # Ensure metadata values are compatible with Chroma (str, int, float, bool)
            safe_metadatas = []
            for c in new_chunks:
                safe_meta = {}
                for k, v in c.metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        safe_meta[k] = v
                    elif isinstance(v, list):
                        safe_meta[k] = ", ".join(map(str, v))
                    else:
                        safe_meta[k] = str(v)
                safe_metadatas.append(safe_meta)
                
            self.collection.upsert(
                ids=[c.chunk_id for c in new_chunks],
                embeddings=new_embeddings.tolist(),
                documents=[c.content for c in new_chunks],
                metadatas=safe_metadatas
            )
            
        # Load all embeddings aligned with self.chunks to maintain RRF compatibility
        if chunks:
            all_data = self.collection.get(ids=[c.chunk_id for c in chunks], include=["embeddings"])
            embedding_dict = {id_: emb for id_, emb in zip(all_data["ids"], all_data["embeddings"])}
            self.chunk_embeddings = np.array([embedding_dict[c.chunk_id] for c in chunks])
        else:
            self.chunk_embeddings = np.array([])
        
        # 3. Initialize Cross-Encoder
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)

    def retrieve(self, query: str, top_k: int = 5, filter_category: str = None) -> List[RetrievalResult]:
        n = len(self.chunks)
        if n == 0:
            return []
            
        # 1. BM25 scoring & ranking
        query_tokens = tokenize(query)
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_ranked_indices = np.argsort(bm25_scores)[::-1]
        
        bm25_ranks = {}
        for rank, idx in enumerate(bm25_ranked_indices):
            bm25_ranks[idx] = rank + 1  # 1-indexed

        # 2. Dense Cosine Similarity scoring & ranking
        query_vec = self.embedder.embed_query(query)
        
        # Cosine similarity
        norm_q = np.linalg.norm(query_vec)
        norm_chunks = np.linalg.norm(self.chunk_embeddings, axis=1)
        denom = norm_q * norm_chunks
        denom[denom == 0] = 1e-9
        cosine_scores = np.dot(self.chunk_embeddings, query_vec) / denom
        
        dense_ranked_indices = np.argsort(cosine_scores)[::-1]
        dense_ranks = {}
        for rank, idx in enumerate(dense_ranked_indices):
            dense_ranks[idx] = rank + 1  # 1-indexed

        # 3. Reciprocal Rank Fusion (RRF)
        # 3. Reciprocal Rank Fusion (RRF) & Metadata Filtering
        rrf_scores = np.zeros(n, dtype=np.float32)
        for idx in range(n):
            # Metadata pre-filtering
            chunk_cat = self.chunks[idx].metadata.get("category", "")
            if filter_category and chunk_cat and filter_category not in chunk_cat:
                rrf_scores[idx] = -1.0 # Mask out
                continue
                
            rrf_bm25 = 1.0 / (self.rrf_k + bm25_ranks[idx])
            rrf_dense = 1.0 / (self.rrf_k + dense_ranks[idx])
            rrf_scores[idx] = rrf_bm25 + rrf_dense
            
        rrf_ranked_indices = np.argsort(rrf_scores)[::-1]
        
        results: List[RetrievalResult] = []
        # Fetch top_k * 2 for the Cross-Encoder to re-rank
        fetch_k = top_k * 2
        
        rrf_rank_idx = 0
        for idx in rrf_ranked_indices:
            if rrf_scores[idx] < 0:
                continue # Filtered out
            if len(results) >= fetch_k:
                break
                
            chunk = self.chunks[idx]
            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    document=chunk.document,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    dense_score=float(cosine_scores[idx]),
                    dense_rank=dense_ranks[idx],
                    bm25_score=float(bm25_scores[idx]),
                    bm25_rank=bm25_ranks[idx],
                    rrf_score=float(rrf_scores[idx]),
                    rrf_rank=rrf_rank_idx + 1,
                )
            )
            rrf_rank_idx += 1
            
        # 4. Cross-Encoder Re-ranking
        if results:
            cross_inp = [[query, r.content] for r in results]
            ce_scores = self.cross_encoder.predict(cross_inp)
            for i, r in enumerate(results):
                r.metadata["cross_encoder_score"] = float(ce_scores[i])
                
            # Sort by CE score and take top_k (we fetched top_k * 2 initially)
            results.sort(key=lambda x: x.metadata["cross_encoder_score"], reverse=True)
            results = results[:top_k]
            
        return results
