import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.db.pgvector_client import get_db
from backend.models.document import DocumentModel, ChunkModel, DocumentStatus
from backend.schemas.chat_schema import DocumentResponse
from backend.services.ingestion_service import IngestionService, MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])
ingestion_service = IngestionService()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and index a new document into the RAG corpus."""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier invalide ou manquant.",
        )

    # 1. Validation de l'extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format de fichier non supporté : '{ext}'. Les formats acceptés sont : pdf, docx, txt.",
        )

    # 2. Lecture et validation de la taille (max 10 Mo)
    try:
        content_bytes = await file.read()
    except Exception as e:
        logger.error(f"Erreur de lecture du fichier uploadé: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de lire le fichier uploadé: {e}",
        )

    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier uploadé est vide.",
        )

    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La taille du fichier ({len(content_bytes) / (1024*1024):.2f} Mo) dépasse la limite de 10 Mo.",
        )

    # 3. Création de l'enregistrement en base
    doc_id = uuid.uuid4()
    doc = DocumentModel(
        id=doc_id,
        filename=filename,
        status=DocumentStatus.Processing,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 4. Ingestion, chunking, embeddings et indexation
    try:
        updated_doc = ingestion_service.process_and_index_document(
            db=db,
            document_id=doc_id,
            filename=filename,
            content_bytes=content_bytes,
        )
        return updated_doc
    except Exception as e:
        logger.exception(f"Erreur lors de l'indexation du document {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement et de l'indexation du document : {str(e)}",
        )


@router.get("", response_model=List[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):
    """Retrieve list of all indexed documents."""
    docs = db.query(DocumentModel).order_by(DocumentModel.uploaded_at.desc()).all()
    return docs


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a document and its associated chunks."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document avec l'ID '{document_id}' introuvable.",
        )

    try:
        # Supprimer explicitement les chunks associés puis le document
        db.query(ChunkModel).filter(ChunkModel.document_id == document_id).delete()
        db.delete(doc)
        db.commit()
        return {"detail": f"Document '{doc.filename}' et ses chunks ont été supprimés avec succès."}
    except Exception as e:
        db.rollback()
        logger.exception(f"Erreur lors de la suppression du document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur serveur lors de la suppression du document: {str(e)}",
        )
