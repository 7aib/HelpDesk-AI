"""
Services for HelpDesk-AI documents app.
Business logic for document processing.
"""

import logging
import time
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Service for processing uploaded documents.
    
    Handles text extraction, cleaning, chunking, and embedding generation.
    """

    def __init__(self):
        """Initialize the document processing service."""
        from apps.rag.services import EmbeddingService

        self.embedding_service = EmbeddingService()

    def process_document(self, document) -> dict[str, Any]:
        """
        Process a document end-to-end.
        
        Args:
            document: The Document instance to process.
            
        Returns:
            Dictionary with processing results.
        """
        start_time = time.time()

        # Step 1: Extract text
        logger.info(f"Extracting text from document: {document.title}")
        text = self._extract_text(document)
        
        if not text.strip():
            raise ValueError("Document is empty or no text could be extracted")

        # Step 2: Clean text
        logger.info("Cleaning text")
        cleaned_text = self._clean_text(text)

        # Step 3: Get page count if PDF
        page_count = self._get_page_count(document)
        if page_count:
            document.page_count = page_count
            document.save(update_fields=["page_count"])

        # Step 4: Chunk text
        logger.info("Chunking text")
        chunks = self._chunk_text(
            cleaned_text,
            chunk_size=document.knowledge_base.chatbot.chunk_size,
            chunk_overlap=document.knowledge_base.chatbot.chunk_overlap,
        )

        # Step 5: Generate embeddings
        logger.info("Generating embeddings")
        chunk_contents = [chunk["content"] for chunk in chunks]
        embeddings = self.embedding_service.generate_embeddings_batch(
            chunk_contents,
            model_name=document.knowledge_base.chatbot.embedding_model,
        )

        # Step 6: Save chunks with embeddings
        logger.info("Saving chunks")
        from apps.knowledge.models import DocumentChunk

        chunk_objects = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_obj = DocumentChunk(
                document=document,
                content=chunk["content"],
                embedding=embedding,
                chunk_index=i,
                page_number=chunk.get("page_number"),
                token_count=chunk.get("token_count", 0),
                metadata=chunk.get("metadata", {}),
            )
            chunk_objects.append(chunk_obj)

        # Bulk create for efficiency
        DocumentChunk.objects.bulk_create(chunk_objects)

        # Update knowledge base stats
        document.knowledge_base.update_stats()

        duration = time.time() - start_time

        return {
            "chunk_count": len(chunks),
            "duration": duration,
            "page_count": page_count,
        }

    def _extract_text(self, document) -> str:
        """
        Extract text from a document based on its type.
        
        Args:
            document: The Document instance.
            
        Returns:
            Extracted text string.
        """
        file_path = document.file.path
        
        if document.document_type == "pdf":
            return self._extract_pdf_text(file_path)
        elif document.document_type == "docx":
            return self._extract_docx_text(file_path)
        elif document.document_type == "txt":
            return self._extract_txt_text(file_path)
        elif document.document_type == "md":
            return self._extract_markdown_text(file_path)
        else:
            raise ValueError(f"Unsupported document type: {document.document_type}")

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        import fitz

        doc = fitz.open(file_path)
        text_parts = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        
        doc.close()
        return "\n\n".join(text_parts)

    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX using python-docx."""
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        return "\n\n".join(text_parts)

    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from TXT file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _extract_markdown_text(self, file_path: str) -> str:
        """Extract text from Markdown file."""
        import re

        import markdown

        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        
        # Convert markdown to plain text
        html = markdown.markdown(md_content)
        # Simple HTML to text conversion
        text = re.sub(r"<[^>]+>", "", html)
        return text

    def _get_page_count(self, document) -> int:
        """Get page count for PDF documents."""
        if document.document_type != "pdf":
            return 0
        
        try:
            import fitz

            doc = fitz.open(document.file.path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text.
            
        Returns:
            Cleaned text.
        """
        import re
        
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r"[^\w\s.,!?;:\-\'\"]+", "", text)
        
        # Normalize line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to chunk.
            chunk_size: Maximum chunk size in characters.
            chunk_overlap: Overlap between chunks.
            
        Returns:
            List of chunk dictionaries.
        """
        chunks = []
        
        # Split by sentences first
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "token_count": len(chunk_text.split()),
                    "metadata": {},
                })
                
                # Start new chunk with overlap
                overlap_text = " ".join(current_chunk[-2:]) if len(current_chunk) > 1 else ""
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_size = len(overlap_text) + sentence_size + 1
            else:
                current_chunk.append(sentence)
                current_size += sentence_size + 1
        
        # Add the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "token_count": len(chunk_text.split()),
                "metadata": {},
            })
        
        return chunks
