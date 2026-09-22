import math
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.ai_copilot import RAGDocument
from ai.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two vector lists."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class RetrievalService:
    """
    Tenant-isolated Retrieval-Augmented Generation (RAG) Service.
    Stores and queries document chunks and CRM embeddings strictly scoped by workspace_id.
    """

    def __init__(self, provider: Optional[OllamaProvider] = None):
        self.provider = provider or OllamaProvider()

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        """Splits long text into overlapping chunks."""
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max(1, chunk_size - overlap)
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            if i + chunk_size >= len(words):
                break
        return chunks

    async def index_document(
        self,
        db: Session,
        workspace_id: int,
        source_type: str,
        content: str,
        source_id: Optional[str] = None,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Chunks content, generates embeddings, and saves records into ai_rag_documents."""
        if not content.strip():
            return 0

        chunks = self.chunk_text(content)
        count = 0
        for idx, chunk in enumerate(chunks):
            embedding = await self.provider.generate_embedding(chunk)
            doc = RAGDocument(
                workspace_id=workspace_id,
                source_type=source_type,
                source_id=source_id,
                title=title,
                content=chunk,
                chunk_index=idx,
                embedding=embedding,
                extra_metadata=metadata or {},
            )
            db.add(doc)
            count += 1
        db.commit()
        return count

    async def search(
        self,
        db: Session,
        workspace_id: int,
        query: str,
        top_k: int = 3,
        source_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most semantically relevant chunks strictly within workspace_id.
        Workspace A can never access Workspace B documents.
        """
        if not query.strip():
            return []

        # 1. SQL query filtered strictly by workspace_id
        db_query = db.query(RAGDocument).filter(RAGDocument.workspace_id == workspace_id)
        if source_type:
            db_query = db_query.filter(RAGDocument.source_type == source_type)

        candidates = db_query.all()
        if not candidates:
            return []

        # 2. Embed query
        query_vec = await self.provider.generate_embedding(query)

        # 3. Score candidates with cosine similarity + keyword boost
        scored = []
        query_words = set(query.lower().split())
        for doc in candidates:
            sim = cosine_similarity(query_vec, doc.embedding or [])
            # Keyword overlap boost for precision
            doc_words = set(doc.content.lower().split())
            overlap = len(query_words.intersection(doc_words)) / max(1, len(query_words))
            score = (sim * 0.7) + (overlap * 0.3)
            scored.append((score, doc))

        # 4. Sort and return top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:top_k]:
            results.append({
                "id": doc.id,
                "score": round(score, 3),
                "title": doc.title,
                "source_type": doc.source_type,
                "source_id": doc.source_id,
                "content": doc.content,
            })
        return results


_retrieval_service = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
