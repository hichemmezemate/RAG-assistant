import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value) if not isinstance(value, uuid.UUID) else value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class DocumentStatus(str, enum.Enum):
    Processing = "Processing"
    Indexed = "Indexed"
    Error = "Error"


class MessageRole(str, enum.Enum):
    User = "User"
    Assistant = "Assistant"


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status = Column(
        SQLEnum(DocumentStatus, name="document_status_enum"),
        default=DocumentStatus.Processing,
        nullable=False,
    )

    chunks = relationship(
        "ChunkModel",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChunkModel(Base):
    __tablename__ = "chunks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        GUID(),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    page_or_section = Column(String(255), nullable=True)

    document = relationship("DocumentModel", back_populates="chunks")


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    role = Column(
        SQLEnum(MessageRole, name="message_role_enum"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True, default=list)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
