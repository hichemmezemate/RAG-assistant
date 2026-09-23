import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from backend.models.document import DocumentStatus, MessageRole


class ChunkSourceResponse(BaseModel):
    documentId: uuid.UUID
    documentName: str
    pageOrSection: Optional[str] = None
    extrait: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    filename: str
    uploaded_at: datetime
    status: DocumentStatus

    @computed_field
    @property
    def uploadedAt(self) -> datetime:
        return self.uploaded_at


class ChatRequest(BaseModel):
    question: str = Field(..., description="Question posée par l'utilisateur")

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("La question ne doit pas être vide.")
        return value.strip()


class EvaluationResult(BaseModel):
    faithfulness: float = Field(..., ge=0.0, le=1.0)
    relevance: float = Field(..., ge=0.0, le=1.0)
    context_usage: float = Field(..., ge=0.0, le=1.0)
    details: Optional[str] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    sources: List[ChunkSourceResponse] = Field(default_factory=list)
    created_at: datetime

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.created_at


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    role: MessageRole = MessageRole.Assistant
    content: str
    sources: List[ChunkSourceResponse] = Field(default_factory=list)
    created_at: datetime
    evaluation: Optional[EvaluationResult] = None

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.created_at


class ErrorResponse(BaseModel):
    detail: str
