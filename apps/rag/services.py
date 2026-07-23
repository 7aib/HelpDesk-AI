"""
Services for HelpDesk-AI RAG app.
Handles embedding generation, vector search, and RAG pipeline.
"""

import json
import logging
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Cache for loaded models (lazy loaded)
_model_cache: dict[str, Any] = {}


class EmbeddingService:
    """
    Service for generating embeddings using local models.

    Supports multiple embedding models with caching to avoid
    reloading models on each request.
    """

    @staticmethod
    def get_model(model_name: str = None) -> Any:
        """
        Get or load an embedding model.

        Args:
            model_name: Name of the model to load.

        Returns:
            The loaded SentenceTransformer model.
        """
        if model_name is None:
            model_name = settings.DEFAULT_EMBEDDING_MODEL

        if model_name not in _model_cache:
            logger.info(f"Loading embedding model: {model_name}")
            try:
                from sentence_transformers import SentenceTransformer

                _model_cache[model_name] = SentenceTransformer(model_name)
                logger.info(f"Successfully loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                raise

        return _model_cache[model_name]

    @staticmethod
    def generate_embedding(
        text: str,
        model_name: str = None,
    ) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for.
            model_name: Name of the model to use.

        Returns:
            List of floats representing the embedding.
        """
        model = EmbeddingService.get_model(model_name)
        embedding = model.encode(text)
        return embedding.tolist()

    @staticmethod
    def generate_embeddings_batch(
        texts: list[str],
        model_name: str = None,
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to generate embeddings for.
            model_name: Name of the model to use.
            batch_size: Batch size for processing.

        Returns:
            List of embeddings.
        """
        model = EmbeddingService.get_model(model_name)
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()

    @staticmethod
    def get_model_dimensions(model_name: str = None) -> int:
        """
        Get the dimension of embeddings for a model.

        Args:
            model_name: Name of the model.

        Returns:
            Embedding dimension.
        """
        model = EmbeddingService.get_model(model_name)
        return model.get_sentence_embedding_dimension()


class VectorSearchService:
    """
    Service for vector similarity search using pgvector.
    """

    @staticmethod
    def search_similar_chunks(
        query_embedding: list[float],
        chatbot_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query_embedding: The query embedding vector.
            chatbot_id: The chatbot ID to search within.
            top_k: Number of results to return.
            similarity_threshold: Minimum similarity score.

        Returns:
            List of similar chunks with scores.
        """
        from django.db import connection

        # Convert embedding to string for pgvector
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # SQL query for vector search using cosine similarity
        sql = """
            SELECT
                dc.id,
                dc.content,
                dc.chunk_index,
                dc.page_number,
                dc.metadata,
                d.title as document_title,
                1 - (dc.embedding <=> %s::vector) as similarity
            FROM knowledge_documentchunk dc
            JOIN documents_document d ON dc.document_id = d.id
            JOIN knowledge_knowledgebase kb ON d.knowledge_base_id = kb.id
            WHERE
                kb.chatbot_id = %s
                AND dc.embedding IS NOT NULL
                AND 1 - (dc.embedding <=> %s::vector) >= %s
            ORDER BY dc.embedding <=> %s::vector
            LIMIT %s
        """

        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [embedding_str, chatbot_id, embedding_str, similarity_threshold, top_k],
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return results

    @staticmethod
    def search_qa_pairs(
        query_embedding: list[float],
        knowledge_base_id: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search for similar Q&A pairs.

        Args:
            query_embedding: The query embedding vector.
            knowledge_base_id: The knowledge base ID.
            top_k: Number of results to return.

        Returns:
            List of similar Q&A pairs.
        """
        from django.db import connection

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = """
            SELECT
                qp.id,
                qp.question,
                qp.answer,
                qp.category,
                1 - (qp.embedding <=> %s::vector) as similarity
            FROM knowledge_qapair qp
            WHERE
                qp.knowledge_base_id = %s
                AND qp.is_active = true
                AND qp.embedding IS NOT NULL
            ORDER BY qp.embedding <=> %s::vector
            LIMIT %s
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, [embedding_str, knowledge_base_id, top_k])
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return results


class OllamaService:
    """
    Service for interacting with Ollama locally.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize the Ollama service.

        Args:
            base_url: Base URL for Ollama API.
        """
        self.base_url = base_url or settings.OLLAMA_URL

    def generate(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = "",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> str:
        """
        Generate a response using Ollama.

        Args:
            prompt: The user prompt.
            model: The model to use.
            system_prompt: System prompt.
            temperature: Temperature for generation.
            top_p: Top P for generation.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.

        Returns:
            Generated response string.
        """
        import requests as http_requests

        if model is None:
            model = settings.DEFAULT_LLM

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }

        try:
            response = http_requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json().get("response", "")

        except http_requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise
        except http_requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def _handle_stream_response(self, response) -> str:
        """Handle streaming response from Ollama."""
        full_response = []
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "response" in chunk:
                    full_response.append(chunk["response"])
        return "".join(full_response)

    def list_models(self) -> list[str]:
        """List available models in Ollama."""
        import requests as http_requests

        url = f"{self.base_url}/api/tags"
        try:
            response = http_requests.get(url, timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []


class RAGPipeline:
    """
    Main RAG pipeline service.
    Combines embedding, search, and generation.
    """

    def __init__(self):
        """Initialize the RAG pipeline."""
        self.embedding_service = EmbeddingService()
        self.search_service = VectorSearchService()
        self.llm_service = OllamaService()

    def answer_question(
        self,
        question: str,
        chatbot,
        conversation_history: list[dict] = None,
    ) -> dict[str, Any]:
        """
        Answer a question using RAG.

        Args:
            question: The user's question.
            chatbot: The chatbot instance.
            conversation_history: Optional conversation history.

        Returns:
            Dictionary with answer and metadata.
        """
        # Generate question embedding
        question_embedding = self.embedding_service.generate_embedding(
            question,
            model_name=chatbot.embedding_model,
        )

        # Search for similar chunks
        similar_chunks = self.search_service.search_similar_chunks(
            query_embedding=question_embedding,
            chatbot_id=str(chatbot.id),
            top_k=chatbot.top_k,
        )

        # Also search Q&A pairs
        qa_pairs = []
        if chatbot.knowledge_base:
            qa_pairs = self.search_service.search_qa_pairs(
                query_embedding=question_embedding,
                knowledge_base_id=str(chatbot.knowledge_base.id),
                top_k=3,
            )

        # Build context
        context = self._build_context(similar_chunks, qa_pairs)

        # Build prompt
        prompt = self._build_prompt(
            question=question,
            context=context,
            conversation_history=conversation_history,
        )

        # Generate answer
        answer = self.llm_service.generate(
            prompt=prompt,
            model=chatbot.llm_model,
            system_prompt=chatbot.system_prompt,
            temperature=chatbot.temperature,
            top_p=chatbot.top_p,
            max_tokens=chatbot.max_context_length,
        )

        return {
            "answer": answer,
            "sources": similar_chunks,
            "qa_pairs_used": qa_pairs,
            "model_used": chatbot.llm_model,
        }

    def _build_context(
        self,
        chunks: list[dict],
        qa_pairs: list[dict],
    ) -> str:
        """
        Build context from chunks and QA pairs.

        Args:
            chunks: Similar document chunks.
            qa_pairs: Similar Q&A pairs.

        Returns:
            Formatted context string.
        """
        context_parts = []

        # Add document chunks
        if chunks:
            context_parts.append("Relevant information from knowledge base:")
            for i, chunk in enumerate(chunks, 1):
                source = chunk.get("document_title", "Unknown")
                content = chunk.get("content", "")
                similarity = chunk.get("similarity", 0)
                context_parts.append(
                    f"\n[Source: {source} (Relevance: {similarity:.2f})]\n{content}"
                )

        # Add Q&A pairs
        if qa_pairs:
            context_parts.append("\n\nRelevant Q&A from knowledge base:")
            for qa in qa_pairs:
                context_parts.append(
                    f"\nQ: {qa['question']}\nA: {qa['answer']}"
                )

        return "\n".join(context_parts) if context_parts else "No relevant information found."

    def _build_prompt(
        self,
        question: str,
        context: str,
        conversation_history: list[dict] = None,
    ) -> str:
        """
        Build the prompt for the LLM.

        Args:
            question: The user's question.
            context: The context from knowledge base.
            conversation_history: Optional conversation history.

        Returns:
            Formatted prompt string.
        """
        prompt_parts = []

        # Add conversation history if available
        if conversation_history:
            prompt_parts.append("Conversation history:")
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.title()}: {content}")
            prompt_parts.append("")

        # Add context
        prompt_parts.append("Context from knowledge base:")
        prompt_parts.append(context)
        prompt_parts.append("")

        # Add question
        prompt_parts.append(f"Question: {question}")
        prompt_parts.append("")
        prompt_parts.append(
            "Instructions: Answer the question based ONLY on the provided context. "
            "If the answer is not in the context, say 'I don't know based on the provided knowledge.' "
            "Do not make up information or hallucinate."
        )

        return "\n".join(prompt_parts)
