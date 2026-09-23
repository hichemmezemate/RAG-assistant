import uuid
import pytest
from backend.services.evaluation_service import EvaluationService


def test_evaluation_metrics_computation():
    eval_service = EvaluationService()

    question = "Quel est le délai de prévenance pour les congés payés ?"
    answer = "Selon le règlement intérieur, le délai de prévenance pour la prise de congés payés est fixé à un mois."
    context = [
        {
            "chunk_id": uuid.uuid4(),
            "content": "Le délai de prévenance pour la prise de congés payés est fixé à un mois à l'avance.",
            "document_name": "reglement.pdf",
        }
    ]
    cited_sources = [
        {
            "documentName": "reglement.pdf",
            "pageOrSection": "Page 4",
            "extrait": "Le délai de prévenance pour la prise de congés payés est fixé à un mois à l'avance.",
        }
    ]

    result = eval_service.evaluate(question, answer, context, cited_sources)

    assert result.faithfulness > 0.5
    assert result.relevance > 0.5
    assert result.context_usage == 1.0


def test_evaluation_empty_context():
    eval_service = EvaluationService()
    question = "Quels sont les objectifs ?"
    answer = "Aucune information trouvée dans les documents."
    result = eval_service.evaluate(question, answer, [], [])

    assert result.context_usage == 0.0
    assert 0.0 <= result.faithfulness <= 1.0
    assert 0.0 <= result.relevance <= 1.0
