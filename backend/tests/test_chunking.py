import pytest
from backend.services.ingestion_service import TextSplitter, IngestionService


def test_chunking_size_and_overlap():
    splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "Le règlement intérieur définit les règles générales d'hygiène et de sécurité au travail. "
        "Tout salarié doit respecter les consignes de sécurité affichées dans les locaux. "
        "En cas d'accident ou de risque grave, alerter immédiatement le responsable de sécurité. "
        "Les équipements de protection individuelle sont obligatoires dans les zones d'atelier."
    )

    chunks = splitter.split_text_with_metadata(sample_text, default_section="Règlement")
    
    assert len(chunks) > 1, "Le texte devrait être découpé en plusieurs chunks"
    for content, section in chunks:
        assert section == "Règlement"
        assert len(content) <= 150  # Respect approximate chunk size with boundary flexibility
        assert len(content.strip()) > 0


def test_chunking_by_sections_markdown_headers():
    splitter = TextSplitter(chunk_size=500, chunk_overlap=50)
    text_with_sections = (
        "# Chapitre 1 - Dispositions Générales\n"
        "Ce chapitre présente le champ d'application et la durée de la convention.\n\n"
        "## Article 1.1 - Champ d'application\n"
        "La présente convention s'applique à l'ensemble du personnel de l'entreprise.\n\n"
        "## Article 1.2 - Période d'essai\n"
        "La période d'essai est fixée à une durée de trois mois renouvelable une fois."
    )

    chunks = splitter.split_text_with_metadata(text_with_sections)
    sections_found = [c[1] for c in chunks]

    assert any("Article 1.1" in s or "Dispositions" in s for s in sections_found)
    assert any("Article 1.2" in s for s in sections_found)


def test_empty_or_whitespace_chunking():
    splitter = TextSplitter()
    assert splitter.split_text_with_metadata("") == []
    assert splitter.split_text_with_metadata("   \n\n  ") == []
