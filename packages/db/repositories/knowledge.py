import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.db.models.knowledge import KnowledgeChunk, KnowledgeDoc


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two dense vectors."""
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class KnowledgeRepository:
    """Repository for managing knowledge documents, chunking, and semantic vector retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_doc(
        self,
        title: str,
        category: str,
        content: str,
        source_file: str | None = None,
        chunks: list[tuple[str, list[float] | None, dict[str, Any] | None]] | None = None,
    ) -> KnowledgeDoc:
        """Create a knowledge document and its associated vector chunks."""
        doc = KnowledgeDoc(
            title=title,
            category=category,
            content=content,
            source_file=source_file,
        )
        self.session.add(doc)
        await self.session.flush()

        if chunks:
            for idx, item in enumerate(chunks):
                chunk_text = item[0]
                embedding = item[1] if len(item) > 1 else None
                meta = item[2] if len(item) > 2 else None

                chunk = KnowledgeChunk(
                    doc_id=doc.id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    metadata_json=meta,
                )
                self.session.add(chunk)
            await self.session.flush()

        return doc

    async def search_semantic(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        category: str | None = None,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Perform semantic cosine similarity search over vector embeddings."""
        stmt = select(KnowledgeChunk).options(selectinload(KnowledgeChunk.document))
        if category:
            stmt = stmt.join(KnowledgeDoc).where(KnowledgeDoc.category == category)

        res = await self.session.execute(stmt)
        all_chunks = list(res.scalars().all())

        scored_chunks: list[tuple[KnowledgeChunk, float]] = []
        for chunk in all_chunks:
            if chunk.embedding is not None and len(chunk.embedding) == len(query_embedding):
                score = cosine_similarity(query_embedding, list(chunk.embedding))
                scored_chunks.append((chunk, score))

        # Sort by similarity descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    async def search_text(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[KnowledgeChunk]:
        """Keyword text search over document chunks."""
        stmt = select(KnowledgeChunk).options(selectinload(KnowledgeChunk.document))
        if category:
            stmt = stmt.join(KnowledgeDoc).where(KnowledgeDoc.category == category)

        res = await self.session.execute(stmt)
        chunks = list(res.scalars().all())

        q_lower = query.lower()
        words = [w for w in q_lower.split() if len(w) > 2]

        matched = []
        for chunk in chunks:
            txt = chunk.chunk_text.lower()
            if q_lower in txt or any(w in txt for w in words):
                matched.append(chunk)

        return matched[:top_k]
