import os
import math
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.document import ChunkModel, DocumentModel
from backend.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


def python_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors in Python."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class RetrievalService:
    def __init__(self, top_k: int = 4, similarity_threshold: float = 0.2):
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.ingestion_service = IngestionService()

    def retrieve_relevant_chunks(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks for a user query.
        Returns a list of dicts with:
        - chunk_id
        - document_id
        - document_name
        - content
        - page_or_section
        - score (similarity score between 0 and 1)
        """
        k = top_k or self.top_k
        query_vectors = self.ingestion_service.generate_embeddings([query])
        if not query_vectors:
            return []
        query_vector = query_vectors[0]

        # Check if database engine dialect is postgresql
        dialect_name = db.bind.dialect.name if db.bind else ""
        results = []

        if dialect_name == "postgresql":
            try:
                # Use pgvector cosine distance operator <=> (cosine distance = 1 - cosine similarity)
                # Distance is ascending (smaller distance = more similar)
                query_stmt = (
                    select(
                        ChunkModel,
                        DocumentModel.filename,
                        (1 - ChunkModel.embedding.cosine_distance(query_vector)).label("similarity"),
                    )
                    .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
                    .filter(ChunkModel.embedding.isnot(None))
                    .order_by(ChunkModel.embedding.cosine_distance(query_vector))
                    .limit(k)
                )

                rows = db.execute(query_stmt).all()
                for chunk, filename, similarity in rows:
                    sim_score = float(similarity) if similarity is not None else 0.0
                    if sim_score >= self.similarity_threshold:
                        results.append({
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "document_name": filename,
                            "content": chunk.content,
                            "page_or_section": chunk.page_or_section or "Général",
                            "score": round(sim_score, 4),
                        })
                return results
            except Exception as e:
                logger.warning(f"Recherche native pgvector a échoué ({e}), fallback en mémoire.")

        # Fallback for SQLite / tests / local runs without pgvector extension loaded
        chunks = (
            db.query(ChunkModel, DocumentModel.filename)
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .filter(ChunkModel.embedding.isnot(None))
            .all()
        )

        scored_chunks = []
        for chunk, filename in chunks:
            raw_emb = chunk.embedding
            # In SQLite or JSON column, embedding might be list or string
            if isinstance(raw_emb, str):
                import json
                try:
                    raw_emb = json.loads(raw_emb)
                except Exception:
                    continue
            if not isinstance(raw_emb, list):
                # If pgvector numpy or vector object
                try:
                    raw_emb = list(raw_emb)
                except Exception:
                    continue

            sim = python_cosine_similarity(query_vector, raw_emb)
            if sim >= self.similarity_threshold:
                scored_chunks.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_name": filename,
                    "content": chunk.content,
                    "page_or_section": chunk.page_or_section or "Général",
                    "score": round(sim, 4),
                })

        # Sort descending by similarity score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:k]
