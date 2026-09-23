import io
import os
import re
import uuid
import logging
from typing import List, Tuple, Optional
from pypdf import PdfReader
import docx
from openai import OpenAI
from sqlalchemy.orm import Session

from backend.models.document import DocumentModel, ChunkModel, DocumentStatus

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 Mo
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class TextSplitter:
    """Intelligent text splitter splitting by hierarchical sections and paragraphs."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n# ", "\n\n## ", "\n\n### ", "\n\n", "\n", ". ", " ", ""]

    def split_text_with_metadata(
        self, text: str, default_section: str = "Général"
    ) -> List[Tuple[str, str]]:
        """Splits text into chunks while preserving paragraph/section context.
        Returns a list of tuples (chunk_content, page_or_section).
        """
        if not text or not text.strip():
            return []

        # Detect sections if present (e.g., Markdown headers or Article/Section headers)
        section_pattern = re.compile(
            r"(?:^|\n)(#{1,4}\s+[^\n]+|Article\s+\d+[^\n]*|Chapitre\s+\d+[^\n]*|Section\s+\d+[^\n]*)",
            re.IGNORECASE,
        )

        matches = list(section_pattern.finditer(text))
        if not matches:
            sections = [(text.strip(), default_section)]
        else:
            sections: List[Tuple[str, str]] = []
            if matches[0].start() > 0:
                prefix = text[: matches[0].start()].strip()
                if prefix:
                    sections.append((prefix, default_section))

            for i, match in enumerate(matches):
                header_raw = match.group(1).lstrip("#").strip()
                start_pos = match.end()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                section_content = text[start_pos:end_pos].strip()
                if section_content:
                    sections.append((section_content, header_raw))

        final_chunks: List[Tuple[str, str]] = []
        for sec_content, sec_title in sections:
            sec_chunks = self._recursive_split(sec_content, self.chunk_size, self.chunk_overlap)
            for c in sec_chunks:
                if c.strip():
                    final_chunks.append((c.strip(), sec_title))

        return final_chunks

    def _recursive_split(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        split_char = None
        for sep in self.separators:
            if sep in text:
                split_char = sep
                break

        if split_char is None or split_char == "":
            # Hard boundary split if no separator found
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(text[start:end])
                if end == len(text):
                    break
                start += max(1, chunk_size - chunk_overlap)
            return chunks

        parts = text.split(split_char)
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part) + len(split_char)
            if current_len + part_len > chunk_size and current_chunk:
                combined = split_char.join(current_chunk)
                chunks.append(combined)
                
                # Overlap logic: keep end of current chunk
                overlap_items = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    if overlap_len + len(item) + len(split_char) <= chunk_overlap:
                        overlap_items.insert(0, item)
                        overlap_len += len(item) + len(split_char)
                    else:
                        break
                current_chunk = overlap_items
                current_len = overlap_len

            current_chunk.append(part)
            current_len += part_len

        if current_chunk:
            chunks.append(split_char.join(current_chunk))

        return chunks


class IngestionService:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    def validate_file(self, filename: str, file_size: int) -> None:
        """Validate filename extension and maximum file size (10 MB)."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Format de fichier non supporté : '{ext}'. Formats acceptés : pdf, docx, txt."
            )
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Taille de fichier dépassée : {file_size / (1024*1024):.2f} Mo. Taille maximale autorisée : 10 Mo."
            )

    def extract_text(self, filename: str, content_bytes: bytes) -> List[Tuple[str, str]]:
        """Extract text and location info from file bytes based on extension.
        Returns a list of (text_segment, page_or_section).
        """
        ext = os.path.splitext(filename)[1].lower()
        segments: List[Tuple[str, str]] = []

        if ext == ".txt":
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1")
            segments.append((text, "Document complet"))

        elif ext == ".pdf":
            reader = PdfReader(io.BytesIO(content_bytes))
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    segments.append((page_text.strip(), f"Page {idx + 1}"))

        elif ext == ".docx":
            doc = docx.Document(io.BytesIO(content_bytes))
            current_section = "Introduction"
            section_paragraphs: List[str] = []

            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue
                if p.style and ("Heading" in p.style.name or "Titre" in p.style.name):
                    if section_paragraphs:
                        segments.append(("\n".join(section_paragraphs), current_section))
                        section_paragraphs = []
                    current_section = f"Section: {text}"
                else:
                    section_paragraphs.append(text)

            if section_paragraphs:
                segments.append(("\n".join(section_paragraphs), current_section))

        return segments

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of texts (1536 dimensions).
        Uses OpenAI or Gemini embeddings when configured, or a deterministic fallback vector.
        """
        if not texts:
            return []

        if self.openai_api_key:
            try:
                client = OpenAI(api_key=self.openai_api_key)
                response = client.embeddings.create(
                    model=self.embedding_model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.error(f"Erreur lors de l'appel OpenAI Embeddings: {e}")
                raise RuntimeError(f"Échec de génération d'embeddings OpenAI: {e}")

        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                
                # Liste ordonnée de modèles d'embeddings supportés par Gemini
                configured_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
                candidates = [configured_model, "models/gemini-embedding-001", "models/gemini-embedding-2", "models/text-embedding-004"]
                
                # Déduplication
                seen = set()
                candidates = [c for c in candidates if not (c in seen or seen.add(c))]

                selected_model = None
                for candidate in candidates:
                    try:
                        res = genai.embed_content(
                            model=candidate,
                            content=texts[0],
                            output_dimensionality=1536,
                        )
                        selected_model = candidate
                        break
                    except Exception:
                        try:
                            res = genai.embed_content(model=candidate, content=texts[0])
                            selected_model = candidate
                            break
                        except Exception:
                            continue

                if not selected_model:
                    raise RuntimeError("Aucun modèle d'embedding Gemini compatible trouvé pour cette clé API.")

                vectors = []
                for text in texts:
                    try:
                        res = genai.embed_content(
                            model=selected_model,
                            content=text,
                            output_dimensionality=1536,
                        )
                    except Exception:
                        res = genai.embed_content(model=selected_model, content=text)
                    raw_emb = res["embedding"]
                    padded = raw_emb + [0.0] * (1536 - len(raw_emb)) if len(raw_emb) < 1536 else raw_emb[:1536]
                    vectors.append(padded)
                return vectors
            except Exception as e:
                logger.error(f"Erreur lors de l'appel Gemini Embeddings ({e}). Utilisation du fallback vectoriel.")

        # Deterministic normalized fallback embedding (1536 dim) for testing / environments without active API keys
        logger.warning("Aucune clé API LLM configurée. Génération d'embeddings vectoriels de secours (1536 dim).")
        vectors = []
        for text in texts:
            import hashlib
            h = hashlib.sha256(text.encode("utf-8")).digest()
            # Generate 1536 float values normalized
            raw_vals = [((h[i % len(h)] + (i * 17) % 255) / 255.0 - 0.5) for i in range(1536)]
            norm = sum(x * x for x in raw_vals) ** 0.5 or 1.0
            vectors.append([x / norm for x in raw_vals])
        return vectors

    def process_and_index_document(
        self,
        db: Session,
        document_id: uuid.UUID,
        filename: str,
        content_bytes: bytes,
    ) -> DocumentModel:
        """Extract text, chunk intelligently, compute embeddings, and store in database."""
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            raise ValueError(f"Document avec id {document_id} introuvable.")

        try:
            doc.status = DocumentStatus.Processing
            db.commit()

            segments = self.extract_text(filename, content_bytes)
            all_chunks: List[Tuple[str, str]] = []

            for seg_text, seg_location in segments:
                chunks = self.text_splitter.split_text_with_metadata(
                    seg_text, default_section=seg_location
                )
                all_chunks.extend(chunks)

            if not all_chunks:
                logger.warning(f"Aucun texte extrait pour le fichier {filename}.")
                doc.status = DocumentStatus.Indexed
                db.commit()
                return doc

            chunk_texts = [c[0] for c in all_chunks]
            embeddings = self.generate_embeddings(chunk_texts)

            for (c_text, c_loc), emb in zip(all_chunks, embeddings):
                chunk_obj = ChunkModel(
                    document_id=doc.id,
                    content=c_text,
                    embedding=emb,
                    page_or_section=c_loc,
                )
                db.add(chunk_obj)

            doc.status = DocumentStatus.Indexed
            db.commit()
            db.refresh(doc)
            logger.info(f"Document {filename} ({doc.id}) indexé avec succès ({len(all_chunks)} chunks).")
            return doc

        except Exception as e:
            db.rollback()
            logger.exception(f"Erreur d'ingestion pour le document {filename}: {e}")
            doc.status = DocumentStatus.Error
            db.commit()
            raise
