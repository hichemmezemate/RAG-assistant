import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.db.pgvector_client import get_db, Base
from backend.models.document import DocumentModel, ChunkModel, MessageModel, DocumentStatus, MessageRole

from sqlalchemy.pool import StaticPool

# In-memory SQLite for route testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_valid_txt_document(client, test_db):
    content = b"# Guide d'onboarding\nBienvenue dans l'entreprise. Votre tuteur est assigne des le premier jour."
    files = {"file": ("onboarding.txt", io.BytesIO(content), "text/plain")}
    
    response = client.post("/api/documents", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "onboarding.txt"
    assert data["status"] == "Indexed"
    assert "id" in data

    # Verify in DB
    doc_in_db = test_db.query(DocumentModel).filter(DocumentModel.filename == "onboarding.txt").first()
    assert doc_in_db is not None
    chunks_count = test_db.query(ChunkModel).filter(ChunkModel.document_id == doc_in_db.id).count()
    assert chunks_count > 0


def test_upload_invalid_file_extension(client):
    files = {"file": ("malicious.exe", io.BytesIO(b"content"), "application/octet-stream")}
    response = client.post("/api/documents", files=files)
    assert response.status_code == 400
    assert "non supporté" in response.json()["detail"]


def test_upload_empty_file(client):
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    response = client.post("/api/documents", files=files)
    assert response.status_code == 400
    assert "vide" in response.json()["detail"]


def test_get_documents_list(client, test_db):
    doc1 = DocumentModel(id=uuid.uuid4(), filename="doc1.pdf", status=DocumentStatus.Indexed)
    doc2 = DocumentModel(id=uuid.uuid4(), filename="doc2.docx", status=DocumentStatus.Indexed)
    test_db.add_all([doc1, doc2])
    test_db.commit()

    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    filenames = [d["filename"] for d in data]
    assert "doc1.pdf" in filenames
    assert "doc2.docx" in filenames


def test_delete_document_success_and_cascade(client, test_db):
    doc_id = uuid.uuid4()
    doc = DocumentModel(id=doc_id, filename="to_delete.txt", status=DocumentStatus.Indexed)
    chunk = ChunkModel(id=uuid.uuid4(), document_id=doc_id, content="Sample content")
    test_db.add(doc)
    test_db.add(chunk)
    test_db.commit()

    response = client.delete(f"/api/documents/{doc_id}")
    assert response.status_code == 200
    assert "supprimés avec succès" in response.json()["detail"]

    # Verify deletion in DB
    assert test_db.query(DocumentModel).filter(DocumentModel.id == doc_id).first() is None
    assert test_db.query(ChunkModel).filter(ChunkModel.document_id == doc_id).first() is None


def test_delete_document_not_found(client):
    random_id = uuid.uuid4()
    response = client.delete(f"/api/documents/{random_id}")
    assert response.status_code == 404


def test_chat_empty_question_validation(client):
    response = client.post("/api/chat", json={"question": "   "})
    assert response.status_code == 400
    assert "vide" in response.json()["detail"]


def test_chat_and_history_flow(client, test_db):
    # 1. Ingest a document
    doc_id = uuid.uuid4()
    doc = DocumentModel(id=doc_id, filename="procedure_teletravail.txt", status=DocumentStatus.Indexed)
    chunk = ChunkModel(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Le télétravail est autorisé à raison de 2 jours par semaine pour les postes éligibles.",
        page_or_section="Article 4",
    )
    # Give it an embedding vector
    chunk.embedding = [0.1] * 1536
    test_db.add(doc)
    test_db.add(chunk)
    test_db.commit()

    # 2. Ask question
    response = client.post("/api/chat", json={"question": "Combien de jours de télétravail sont autorisés ?"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "Assistant"
    assert "content" in data
    assert len(data["content"]) > 0
    assert "evaluation" in data
    assert "faithfulness" in data["evaluation"]

    # 3. Retrieve history
    history_response = client.get("/api/chat/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 2  # 1 User message + 1 Assistant message
    assert history[0]["role"] == "User"
    assert history[1]["role"] == "Assistant"

    # 4. Clear chat history
    delete_response = client.delete("/api/chat/history")
    assert delete_response.status_code == 200
    assert "réinitialisé avec succès" in delete_response.json()["detail"]

    # 5. Verify history is empty
    empty_history = client.get("/api/chat/history")
    assert empty_history.status_code == 200
    assert len(empty_history.json()) == 0
