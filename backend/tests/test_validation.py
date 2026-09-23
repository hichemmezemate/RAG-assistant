import pytest
from pydantic import ValidationError
from backend.services.ingestion_service import IngestionService, MAX_FILE_SIZE_BYTES
from backend.schemas.chat_schema import ChatRequest


def test_file_validation_valid_formats():
    service = IngestionService()
    # Shouldn't raise any error
    service.validate_file("reglement.pdf", 1024)
    service.validate_file("procedure.docx", 2048)
    service.validate_file("notes.txt", 512)


def test_file_validation_invalid_formats():
    service = IngestionService()
    invalid_files = ["script.exe", "data.csv", "archive.zip", "image.png"]
    for filename in invalid_files:
        with pytest.raises(ValueError, match="Format de fichier non supporté"):
            service.validate_file(filename, 1024)


def test_file_validation_size_limit():
    service = IngestionService()
    oversized = MAX_FILE_SIZE_BYTES + 1
    with pytest.raises(ValueError, match="Taille de fichier dépassée"):
        service.validate_file("gros_document.pdf", oversized)


def test_chat_request_validation():
    # Valid question
    req = ChatRequest(question="Quelle est la procédure ?")
    assert req.question == "Quelle est la procédure ?"

    # Empty question
    with pytest.raises(ValidationError):
        ChatRequest(question="")

    # Whitespace only question
    with pytest.raises(ValidationError):
        ChatRequest(question="     \n  \t  ")
