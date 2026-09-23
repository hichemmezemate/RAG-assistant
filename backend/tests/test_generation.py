import uuid
import pytest
from unittest.mock import MagicMock, patch
from backend.services.generation_service import GenerationService


def test_generation_local_synthesizer_fallback():
    service = GenerationService()
    # Ensure no API keys are used for this test
    service.openai_api_key = None
    service.anthropic_api_key = None

    context = [
        {
            "chunk_id": uuid.uuid4(),
            "document_id": uuid.uuid4(),
            "document_name": "guide_rh.pdf",
            "content": "Le temps de travail hebdomadaire est fixé à 35 heures.",
            "page_or_section": "Page 5",
            "score": 0.85,
        }
    ]

    answer, sources = service.generate_response("Combien d'heures par semaine ?", context)

    assert "guide_rh.pdf" in answer or len(sources) > 0
    assert len(sources) == 1
    assert sources[0]["documentName"] == "guide_rh.pdf"
    assert sources[0]["pageOrSection"] == "Page 5"
    assert "35 heures" in sources[0]["extrait"]


def test_generation_mock_openai():
    service = GenerationService()
    service.provider = "openai"
    service.openai_api_key = "sk-mock-test-key"

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Selon le règlement [Source: guide_rh.pdf, Page 5], la durée est de 35h."
    mock_response.choices = [mock_choice]

    context = [
        {
            "chunk_id": uuid.uuid4(),
            "document_id": uuid.uuid4(),
            "document_name": "guide_rh.pdf",
            "content": "La durée de travail est de 35 heures par semaine.",
            "page_or_section": "Page 5",
            "score": 0.9,
        }
    ]

    with patch("backend.services.generation_service.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        answer, sources = service.generate_response("Quelle est la durée ?", context)

        assert "35h" in answer
        assert len(sources) == 1
        assert sources[0]["documentName"] == "guide_rh.pdf"


def test_generation_mock_anthropic():
    service = GenerationService()
    service.provider = "anthropic"
    service.anthropic_api_key = "anthropic-mock-test-key"

    mock_response = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = "Conformément à la convention [Source: convention.docx, Article 2], les congés sont de 25 jours."
    mock_response.content = [mock_content_block]

    context = [
        {
            "chunk_id": uuid.uuid4(),
            "document_id": uuid.uuid4(),
            "document_name": "convention.docx",
            "content": "Le nombre de jours de congés payés annuels est fixé à 25 jours ouvrés.",
            "page_or_section": "Article 2",
            "score": 0.88,
        }
    ]

    with patch("backend.services.generation_service.anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        answer, sources = service.generate_response("Combien de congés ?", context)

        assert "25 jours" in answer
        assert len(sources) == 1
        assert sources[0]["documentName"] == "convention.docx"


def test_generation_mock_gemini():
    service = GenerationService()
    service.provider = "gemini"
    service.gemini_api_key = "gemini-mock-test-key"

    mock_response = MagicMock()
    mock_response.text = "Selon le guide de télétravail [Source: teletravail.pdf, Page 1], 2 jours sont autorisés."

    context = [
        {
            "chunk_id": uuid.uuid4(),
            "document_id": uuid.uuid4(),
            "document_name": "teletravail.pdf",
            "content": "Le télétravail est fixé à 2 jours par semaine.",
            "page_or_section": "Page 1",
            "score": 0.92,
        }
    ]

    with patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_model

        answer, sources = service.generate_response("Combien de jours ?", context)

        assert "2 jours" in answer
        assert len(sources) == 1
        assert sources[0]["documentName"] == "teletravail.pdf"
