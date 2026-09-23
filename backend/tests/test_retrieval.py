import uuid
import pytest
from unittest.mock import MagicMock
from backend.services.retrieval_service import RetrievalService, python_cosine_similarity
from backend.models.document import ChunkModel, DocumentModel


def test_python_cosine_similarity():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    assert python_cosine_similarity(vec1, vec2) == pytest.approx(1.0)
    assert python_cosine_similarity(vec1, vec3) == pytest.approx(0.0)
    assert python_cosine_similarity([], []) == 0.0


def test_retrieval_ranking_with_mock_db():
    retrieval_service = RetrievalService(top_k=2, similarity_threshold=0.1)

    # Mock embeddings generator to return controlled vector
    doc_id = uuid.uuid4()
    dummy_doc = DocumentModel(id=doc_id, filename="procedure_securite.pdf")
    
    # 3 chunks with varying mock embeddings
    query_vector = [1.0] + [0.0] * 1535
    retrieval_service.ingestion_service.generate_embeddings = MagicMock(return_value=[query_vector])

    chunk1 = ChunkModel(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Les consignes d'évacuation en cas d'incendie.",
        embedding=[0.95] + [0.0] * 1535,
        page_or_section="Page 3",
        document=dummy_doc,
    )
    chunk2 = ChunkModel(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Procédure de remboursement des frais de déplacement.",
        embedding=[0.1] + [0.0] * 1535,
        page_or_section="Page 8",
        document=dummy_doc,
    )

    mock_db = MagicMock()
    mock_db.bind.dialect.name = "sqlite"
    mock_query = MagicMock()
    mock_query.join.return_value.filter.return_value.all.return_value = [
        (chunk1, "procedure_securite.pdf"),
        (chunk2, "procedure_securite.pdf"),
    ]
    mock_db.query.return_value = mock_query

    results = retrieval_service.retrieve_relevant_chunks(mock_db, "Quelles sont les consignes d'évacuation ?")

    assert len(results) >= 1
    assert results[0]["chunk_id"] == chunk1.id
    assert results[0]["score"] > 0.8
    assert results[0]["document_name"] == "procedure_securite.pdf"
