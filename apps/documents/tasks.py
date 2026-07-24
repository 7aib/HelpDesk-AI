"""
Celery tasks for HelpDesk-AI documents app.
Handles asynchronous document processing.
"""

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document_task(self, document_id: str) -> dict[str, Any]:
    """
    Process an uploaded document asynchronously.
    
    Steps:
    1. Extract text from document
    2. Clean and normalize text
    3. Split into chunks
    4. Generate embeddings
    5. Store in database
    
    Args:
        document_id: The document ID to process.
        
    Returns:
        Dictionary with processing results.
    """
    from apps.documents.models import Document, DocumentProcessLog
    from apps.documents.services import DocumentProcessingService

    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {"error": "Document not found"}

    # Mark as processing
    document.mark_processing()

    # Create log entry
    log = DocumentProcessLog.objects.create(
        document=document,
        event="process",
        status="started",
    )

    try:
        # Process document
        processor = DocumentProcessingService()
        result = processor.process_document(document)

        # Mark as completed
        document.mark_completed(chunk_count=result.get("chunk_count", 0))

        # Update log
        log.status = "completed"
        log.message = f"Processed {result.get('chunk_count', 0)} chunks"
        log.duration = result.get("duration", 0)
        log.save()

        logger.info(f"Document {document_id} processed successfully")
        return result

    except Exception as e:
        # Mark as failed
        document.mark_failed(str(e))

        # Update log
        log.status = "failed"
        log.message = str(e)
        log.save()

        logger.error(f"Document {document_id} processing failed: {e}")

        # Retry if retries remaining
        raise self.retry(exc=e, countdown=60)


@shared_task
def delete_document_task(document_id: str) -> dict[str, str]:
    """
    Delete a document and its chunks.
    
    Args:
        document_id: The document ID to delete.
        
    Returns:
        Dictionary with deletion status.
    """
    from apps.documents.models import Document

    try:
        document = Document.objects.get(id=document_id)
        
        # Delete associated chunks
        from apps.documents.models import DocumentChunk
        
        DocumentChunk.objects.filter(document=document).delete()
        
        # Delete the file
        if document.file:
            document.file.delete()
        
        # Soft delete the document
        document.soft_delete()
        
        logger.info(f"Document {document_id} deleted successfully")
        return {"status": "deleted"}
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {"error": "Document not found"}


@shared_task
def reprocess_document_task(document_id: str) -> dict[str, Any]:
    """
    Reprocess a document (delete old chunks and reprocess).
    
    Args:
        document_id: The document ID to reprocess.
        
    Returns:
        Dictionary with processing results.
    """
    from apps.documents.models import Document
    from apps.knowledge.models import DocumentChunk

    try:
        document = Document.objects.get(id=document_id)
        
        # Delete existing chunks
        DocumentChunk.objects.filter(document=document).delete()
        
        # Reset document status
        document.status = "pending"
        document.chunk_count = 0
        document.error_message = ""
        document.save(update_fields=["status", "chunk_count", "error_message"])
        
        # Process again
        return process_document_task.delay(document_id)
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {"error": "Document not found"}
