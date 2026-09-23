import os
import re
import uuid
import logging
from typing import List, Dict, Any, Tuple
from openai import OpenAI
import anthropic

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu es un assistant IA professionnel spécialisé dans l'analyse de documents métier (documentation interne, textes réglementaires).
Ton rôle est de répondre avec précision et clarté à la question de l'utilisateur EN TE BASANT STRICTEMENT sur les extraits de documents fournis dans le contexte ci-dessous.

Règles impératives :
1. Fonde ta réponse UNIQUEMENT sur les extraits fournis. Si le contexte ne contient pas l'information suffisante pour répondre, dis clairement que l'information n'est pas présente dans les documents disponibles.
2. Chaque affirmation clé DOIT être sourcée en mentionnant le nom du document et la page ou section correspondante entre crochets, par exemple : [Source: convention.pdf, Page 1] ou [Source: reglement.docx, Section: Sécurité].
3. Ne fais aucune supposition qui ne soit pas étayée par le contexte.
4. Reste professionnel, synthétique et courtois.
"""


class GenerationService:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def _format_context(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a prompt context."""
        if not context_chunks:
            return "Aucun document pertinent trouvé dans le corpus."

        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            doc_name = chunk.get("document_name", "Document inconnu")
            loc = chunk.get("page_or_section", "Section générale")
            content = chunk.get("content", "").strip()
            context_parts.append(
                f"--- EXTRAIT {i} ---\nDocument : {doc_name}\nPage/Section : {loc}\nContenu :\n{content}\n"
            )
        return "\n".join(context_parts)

    def generate_response(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate an AI response based on the question and context chunks.
        Returns a tuple: (answer_text, cited_sources)
        """
        context_text = self._format_context(context_chunks)
        user_prompt = f"Contexte extrait des documents métier :\n{context_text}\n\nQuestion de l'utilisateur :\n{question}"

        answer = ""
        # 1. Try Google Gemini if provider is gemini and key exists
        if self.provider == "gemini" and self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                model_candidates = [
                    self.gemini_model,
                    "gemini-3.6-flash",
                    "gemini-flash-latest",
                    "gemini-2.5-flash-lite",
                ]
                # Déduplication
                seen = set()
                model_candidates = [m for m in model_candidates if not (m in seen or seen.add(m))]

                chat_history = []
                if conversation_history:
                    for msg in conversation_history[-6:]:
                        role = "user" if msg.get("role") in ["User", "user"] else "model"
                        chat_history.append({"role": role, "parts": [msg.get("content", "")]})

                last_err = None
                for m_name in model_candidates:
                    try:
                        model = genai.GenerativeModel(
                            model_name=m_name,
                            system_instruction=SYSTEM_PROMPT,
                        )
                        if chat_history:
                            chat = model.start_chat(history=chat_history)
                            response = chat.send_message(user_prompt)
                        else:
                            response = model.generate_content(user_prompt)

                        answer = response.text or ""
                        break
                    except Exception as err:
                        last_err = err
                        logger.warning(f"Échec avec le modèle Gemini '{m_name}': {err}. Tentative avec le suivant...")

                if not answer and last_err:
                    raise last_err
            except Exception as e:
                logger.error(f"Erreur API Google Gemini: {e}")
                raise RuntimeError(f"Échec de l'appel LLM Gemini: {e}")

        # 2. Try Anthropic if provider is anthropic and key exists
        elif self.provider == "anthropic" and self.anthropic_api_key:
            try:
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                messages = []
                if conversation_history:
                    for msg in conversation_history[-6:]:  # Last 3 turns
                        role = "user" if msg.get("role") in ["User", "user"] else "assistant"
                        messages.append({"role": role, "content": msg.get("content", "")})
                messages.append({"role": "user", "content": user_prompt})

                response = client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                )
                answer = response.content[0].text
            except Exception as e:
                logger.error(f"Erreur API Anthropic: {e}")
                raise RuntimeError(f"Échec de l'appel LLM Anthropic: {e}")

        # 2. Try OpenAI if provider is openai and key exists
        elif self.openai_api_key:
            try:
                client = OpenAI(api_key=self.openai_api_key)
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                if conversation_history:
                    for msg in conversation_history[-6:]:
                        role = "user" if msg.get("role") in ["User", "user"] else "assistant"
                        messages.append({"role": role, "content": msg.get("content", "")})
                messages.append({"role": "user", "content": user_prompt})

                response = client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=0.2,
                )
                answer = response.choices[0].message.content or ""
            except Exception as e:
                logger.error(f"Erreur API OpenAI: {e}")
                raise RuntimeError(f"Échec de l'appel LLM OpenAI: {e}")

        # 3. Fallback / Test / Offline synthesizer
        else:
            logger.info("Mode sans clé API externe : utilisation du synthétiseur de réponse local.")
            if not context_chunks:
                answer = (
                    "D'après les documents actuellement indexés, aucune information pertinente n'a été trouvée "
                    "pour répondre à votre question. Veuillez ajouter des documents métier pertinents au corpus."
                )
            else:
                cited_refs = []
                highlights = []
                for c in context_chunks:
                    doc_name = c.get("document_name", "Document")
                    loc = c.get("page_or_section", "Général")
                    content = c.get("content", "")
                    cited_refs.append(f"[Source: {doc_name}, {loc}]")
                    # Take first sentence or up to 150 chars
                    first_sent = content.split("\n")[0][:150]
                    highlights.append(f"- Selon {doc_name} ({loc}) : « {first_sent}... » {cited_refs[-1]}")

                answer = (
                    f"D'après les documents métier analysés, voici les éléments de réponse concernant votre question :\n\n"
                    + "\n".join(highlights)
                    + f"\n\nCes informations sont directement extraites des sources citées."
                )

        # Build list of cited sources from context_chunks matching the answer
        cited_sources = self._extract_cited_sources(answer, context_chunks)
        return answer, cited_sources

    def _extract_cited_sources(
        self, answer: str, context_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify which context chunks are actually cited or relevant to the answer."""
        if not context_chunks:
            return []

        cited: List[Dict[str, Any]] = []
        seen_chunk_ids = set()

        for chunk in context_chunks:
            chunk_id = chunk.get("chunk_id")
            if chunk_id in seen_chunk_ids:
                continue

            doc_name = chunk.get("document_name", "")
            loc = chunk.get("page_or_section", "")
            content = chunk.get("content", "")

            # If document name is in the answer, or if chunk has high relevance
            is_explicitly_cited = doc_name and (doc_name.lower() in answer.lower())
            is_top_result = chunk.get("score", 0.0) >= 0.35

            if is_explicitly_cited or is_top_result or len(context_chunks) <= 2:
                seen_chunk_ids.add(chunk_id)
                # Excerpt up to 250 characters
                excerpt = content[:250].strip()
                if len(content) > 250:
                    excerpt += "..."

                cited.append({
                    "documentId": chunk.get("document_id"),
                    "documentName": doc_name,
                    "pageOrSection": loc,
                    "extrait": excerpt,
                })

        return cited
