import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.pgvector_client import get_db
from backend.models.document import MessageModel, MessageRole
from backend.schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    MessageResponse,
    ChunkSourceResponse,
)
from backend.services.retrieval_service import RetrievalService
from backend.services.generation_service import GenerationService
from backend.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

retrieval_service = RetrievalService()
generation_service = GenerationService()
evaluation_service = EvaluationService()


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def ask_question(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    """Ask a question to the RAG system and receive a sourced response."""
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La question ne doit pas être vide.",
        )

    # 1. Enregistrer le message de l'utilisateur
    user_msg = MessageModel(
        id=uuid.uuid4(),
        role=MessageRole.User,
        content=question,
        sources=[],
    )
    db.add(user_msg)
    db.commit()

    # 2. Récupérer les chunks pertinents via recherche vectorielle
    try:
        relevant_chunks = retrieval_service.retrieve_relevant_chunks(db, question)
    except Exception as e:
        logger.exception(f"Erreur lors de la recherche vectorielle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la recherche vectorielle: {str(e)}",
        )

    # 3. Récupérer l'historique récent de la conversation
    recent_messages = (
        db.query(MessageModel)
        .order_by(MessageModel.created_at.desc())
        .limit(6)
        .all()
    )
    history = [
        {"role": m.role.value, "content": m.content}
        for m in reversed(recent_messages)
    ]

    # 4. Générer la réponse via LLM avec citations de sources
    try:
        answer_text, cited_sources = generation_service.generate_response(
            question=question,
            context_chunks=relevant_chunks,
            conversation_history=history,
        )
    except Exception as e:
        logger.exception(f"Erreur lors de l'appel au modèle de génération: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la génération de réponse: {str(e)}",
        )

    # 5. Évaluation de la réponse (faithfulness, relevance, context usage)
    eval_result = evaluation_service.evaluate(
        question=question,
        answer=answer_text,
        context_chunks=relevant_chunks,
        cited_sources=cited_sources,
    )

    # 6. Enregistrer le message de l'assistant avec ses sources
    serializable_sources = [
        {
            "documentId": str(s["documentId"]),
            "documentName": str(s["documentName"]),
            "pageOrSection": s.get("pageOrSection"),
            "extrait": s["extrait"],
        }
        for s in cited_sources
    ]
    assistant_msg = MessageModel(
        id=uuid.uuid4(),
        role=MessageRole.Assistant,
        content=answer_text,
        sources=serializable_sources,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # 7. Formater et retourner la réponse
    sources_formatted = [
        ChunkSourceResponse(
            documentId=uuid.UUID(s["documentId"]) if isinstance(s["documentId"], str) else s["documentId"],
            documentName=s["documentName"],
            pageOrSection=s.get("pageOrSection"),
            extrait=s["extrait"],
        )
        for s in serializable_sources
    ]

    return ChatResponse(
        id=assistant_msg.id,
        role=MessageRole.Assistant,
        content=assistant_msg.content,
        sources=sources_formatted,
        created_at=assistant_msg.created_at,
        evaluation=eval_result,
    )


@router.get("/history", response_model=List[MessageResponse])
def get_chat_history(db: Session = Depends(get_db)):
    """Retrieve all conversation messages in chronological order."""
    messages = db.query(MessageModel).order_by(MessageModel.created_at.asc()).all()
    
    result = []
    for m in messages:
        sources_list = []
        if m.sources and isinstance(m.sources, list):
            for s in m.sources:
                if isinstance(s, dict):
                    sources_list.append(
                        ChunkSourceResponse(
                            documentId=s.get("documentId"),
                            documentName=s.get("documentName", "Document"),
                            pageOrSection=s.get("pageOrSection"),
                            extrait=s.get("extrait", ""),
                        )
                    )
        result.append(
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=sources_list,
                created_at=m.created_at,
            )
        )
    return result


@router.delete("/history", status_code=status.HTTP_200_OK)
def clear_chat_history(db: Session = Depends(get_db)):
    """Delete all conversation messages from history."""
    try:
        db.query(MessageModel).delete()
        db.commit()
        return {"detail": "Historique de conversation réinitialisé avec succès."}
    except Exception as e:
        db.rollback()
        logger.exception(f"Erreur lors de la réinitialisation de l'historique: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la réinitialisation: {str(e)}",
        )
