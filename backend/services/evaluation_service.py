import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.schemas.chat_schema import EvaluationResult

logger = logging.getLogger(__name__)

# Structured audit logger
audit_logger = logging.getLogger("rag_audit")
audit_logger.setLevel(logging.INFO)
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", "audit.log")

# Setup file handler for audit logging if not already configured
if not audit_logger.handlers:
    try:
        fh = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        fh.setFormatter(formatter)
        audit_logger.addHandler(fh)
    except Exception as e:
        logger.warning(f"Impossible de créer le fichier d'audit {AUDIT_LOG_FILE}: {e}")


class EvaluationService:
    def _extract_keywords(self, text: str) -> set:
        """Extract alphanumeric words with length > 3 for metric computations."""
        words = re.findall(r"\b[a-zA-ZÀ-ÿ0-9_-]{4,}\b", text.lower())
        stopwords = {
            "dans", "pour", "avec", "cette", "sont", "être", "avoir", "nous", "vous",
            "leur", "plus", "tout", "tous", "faire", "ainsi", "selon", "entre", "après",
            "avant", "alors", "aussi", "comme", "dont", "même", "sans", "sous", "vers",
            "from", "with", "that", "this", "have", "were", "what", "when", "which",
        }
        return {w for w in words if w not in stopwords}

    def evaluate(
        self,
        question: str,
        answer: str,
        context_chunks: List[Dict[str, Any]],
        cited_sources: List[Dict[str, Any]],
    ) -> EvaluationResult:
        """Compute evaluation metrics: faithfulness, relevance, context_usage."""
        question_words = self._extract_keywords(question)
        answer_words = self._extract_keywords(answer)

        # Context text aggregated
        context_text = " ".join([c.get("content", "") for c in context_chunks])
        context_words = self._extract_keywords(context_text)

        # 1. Faithfulness: proportion of answer keywords grounded in context
        if not answer_words or not context_words:
            faithfulness = 0.5 if not context_chunks else 0.8
        else:
            supported = answer_words.intersection(context_words)
            faithfulness = min(1.0, max(0.1, len(supported) / max(1, len(answer_words))))

        # 2. Relevance: alignment between question and answer
        if not question_words or not answer_words:
            relevance = 0.5
        else:
            overlap = question_words.intersection(answer_words)
            relevance = min(1.0, max(0.2, (len(overlap) * 2) / (len(question_words) + len(answer_words)) + 0.3))

        # 3. Context Usage: ratio of retrieved chunks that contributed to cited sources
        if not context_chunks:
            context_usage = 0.0
        else:
            context_usage = min(1.0, len(cited_sources) / max(1, len(context_chunks)))

        result = EvaluationResult(
            faithfulness=round(float(faithfulness), 3),
            relevance=round(float(relevance), 3),
            context_usage=round(float(context_usage), 3),
            details=f"Evalué sur {len(context_chunks)} chunks récupérés et {len(cited_sources)} sources citées.",
        )

        # Log for audit
        self.log_audit(
            question=question,
            answer=answer,
            cited_sources=cited_sources,
            evaluation=result,
        )

        return result

    def log_audit(
        self,
        question: str,
        answer: str,
        cited_sources: List[Dict[str, Any]],
        evaluation: EvaluationResult,
    ) -> None:
        """Write audit entry for RAG inquiry and response quality."""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "answer_preview": answer[:200] + ("..." if len(answer) > 200 else ""),
            "sources_count": len(cited_sources),
            "sources": [
                {
                    "documentName": s.get("documentName"),
                    "pageOrSection": s.get("pageOrSection"),
                }
                for s in cited_sources
            ],
            "metrics": {
                "faithfulness": evaluation.faithfulness,
                "relevance": evaluation.relevance,
                "context_usage": evaluation.context_usage,
            },
        }
        audit_logger.info(json.dumps(audit_entry, ensure_ascii=False))
