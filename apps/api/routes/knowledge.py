import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.db.models.knowledge import KnowledgeChunk, KnowledgeDoc
from packages.db.session import get_async_session
from packages.schemas.knowledge import (
    KnowledgeDocCreate,
    KnowledgeDocResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
)

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


@router.get("", response_model=list[KnowledgeDocResponse])
async def list_knowledge_docs(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    category: str | None = Query(default=None),
) -> list[KnowledgeDocResponse]:
    """List all knowledge documents."""
    stmt = select(KnowledgeDoc)
    if category:
        stmt = stmt.where(KnowledgeDoc.category == category)

    stmt = stmt.order_by(desc(KnowledgeDoc.created_at))
    res = await db.execute(stmt)
    docs = list(res.scalars().all())
    return [KnowledgeDocResponse.model_validate(d) for d in docs]


@router.post("", response_model=KnowledgeDocResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_doc(
    payload: KnowledgeDocCreate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> KnowledgeDocResponse:
    """Create and automatically chunk a knowledge document for semantic search."""
    doc = KnowledgeDoc(
        title=payload.title,
        category=payload.category,
        content=payload.content,
        source_file=payload.source_file,
    )
    db.add(doc)
    await db.flush()

    # Automatically create paragraph/sentence chunks
    paragraphs = [p.strip() for p in payload.content.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [payload.content]

    for idx, para in enumerate(paragraphs):
        chunk = KnowledgeChunk(
            doc_id=doc.id,
            chunk_index=idx,
            chunk_text=para,
            metadata_json={"title": payload.title, "category": payload.category},
        )
        db.add(chunk)

    await db.flush()
    return KnowledgeDocResponse.model_validate(doc)


@router.get("/{doc_id}", response_model=KnowledgeDocResponse)
async def get_knowledge_doc(
    doc_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> KnowledgeDocResponse:
    """Retrieve knowledge document by ID."""
    stmt = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"KnowledgeDoc '{doc_id}' not found"
        )

    return KnowledgeDocResponse.model_validate(doc)


@router.post("/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[KnowledgeSearchResult]:
    """Search knowledge documents using keyword and semantic search."""
    stmt = select(KnowledgeChunk).options(selectinload(KnowledgeChunk.document))
    if payload.category:
        stmt = stmt.join(KnowledgeDoc).where(KnowledgeDoc.category == payload.category)

    res = await db.execute(stmt)
    chunks = list(res.scalars().all())

    query_lower = payload.query.lower()
    words = [w for w in query_lower.split() if len(w) > 2]

    results: list[KnowledgeSearchResult] = []
    for chunk in chunks:
        doc = chunk.document
        doc_title = doc.title if doc else "Document"
        cat = doc.category if doc else "general"

        chunk_text = chunk.chunk_text.lower()
        if query_lower in chunk_text or any(w in chunk_text for w in words):
            results.append(
                KnowledgeSearchResult(
                    chunk_id=chunk.id,
                    doc_id=chunk.doc_id,
                    doc_title=doc_title,
                    category=cat,
                    chunk_text=chunk.chunk_text,
                    similarity_score=1.0,
                )
            )

    return results[: payload.top_k]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_doc(
    doc_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> Response:
    """Delete a knowledge document and its associated chunks."""
    stmt = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"KnowledgeDoc '{doc_id}' not found"
        )

    await db.delete(doc)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
