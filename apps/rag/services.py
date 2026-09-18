"""
Services for HelpDesk-AI RAG app.
Handles embedding generation, vector search, and RAG pipeline.
"""

import json
import logging
import uuid
from typing import Any, ClassVar, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Cache for loaded models (lazy loaded)
_model_cache: dict[str, Any] = {}

DEFAULT_MAX_TOKENS = 500

TOKENS_PER_WORD = 1.3

_spellchecker = None


def _get_spellchecker():
    """Lazily load the shared English spellchecker."""
    global _spellchecker
    if _spellchecker is None:
        from spellchecker import SpellChecker

        _spellchecker = SpellChecker(language="en")
    return _spellchecker


def _levenshtein(a: str, b: str) -> int:
    """Levenshtein edit distance between two short strings."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def _levenshtein_best_match(word: str, possibilities: list[str], cutoff: float):
    """Return the closest vocabulary word by normalized edit distance."""
    best = None
    best_score = 0.0
    for candidate in possibilities:
        ratio = 1.0 - (_levenshtein(word, candidate) / max(len(word), len(candidate)))
        if ratio > best_score:
            best_score = ratio
            best = candidate
    if best is not None and best_score >= cutoff:
        return best
    return None


def estimate_tokens(text: str) -> int:
    """Rough token estimate for English text (~1.3 tokens per word)."""
    if not text:
        return 0
    return max(1, int(len(text.split()) * TOKENS_PER_WORD))


def truncate_to_tokens(text: str, token_budget: int) -> str:
    """Truncate text from the front to fit within a token budget."""
    if not text:
        return text
    if token_budget <= 0:
        return ""
    word_budget = max(1, int(token_budget / TOKENS_PER_WORD))
    words = text.split()
    if len(words) <= word_budget:
        return text
    return " ".join(words[:word_budget])


class QueryCorrector:
    """
    Domain-aware spelling correction for user queries.

    A misspelled query shifts its embedding away from the indexed text
    and collapses retrieval. This corrects words in a user question that
    are unknown to the knowledge base, matching them (edit-distance based)
    to the closest term actually used in the chatbot's documents / Q&A
    pairs before embedding. Vocabulary is cached per knowledge base and
    invalidated when the knowledge base changes.
    """

    _vocab_cache: ClassVar[dict[str, tuple[str, frozenset]]] = {}

    MIN_WORD_LENGTH = 3
    DOMAIN_MATCH_CUTOFF = 0.7
    MAX_ENGLISH_EDIT_DISTANCE = 1
    MAX_VOCAB_WORDS = 8000

    # Common English words are never "corrected"; they are always accepted
    # so frequent vocabulary outside a small knowledge base stays intact.
    COMMON_WORDS = frozenset(
        """
        a about above after again against all am an and any are aren't as at
        be because been before being below between both but by can can't cannot
        could couldn't did didn't do does doesn't doing don't down during each
        few for from further had hadn't has hasn't have haven't having he he'd
        he'll he's her here here's hers herself him himself his how how's i i'd
        i'll i'm i've if in into is isn't it it's its itself let's me more most
        mustn't my myself no nor not of off on once only or other ought our
        ours ourselves out over own same shan't she she'd she'll she's should
        shouldn't so some such than that that's the their theirs them themselves
        then there there's these they they'd they'll they're they've this those
        through to too under until up very was wasn't we we'd we'll we're we've
        were weren't what what's when when's where where's which while who
        who's whom why why's with won't would wouldn't you you'd you'll you're
        you've your yours yourself yourselves can please help need want got
        like much many some thing things question answer info information know
        how what why where when thanks thank would could should do does did
        about around place need make back time order now refund return shipping
        track number account password reset code payment billing customer
        support service product price cost date total item items list see show
        status details detail sign update change
        """.split()  # noqa: SIM905 - word list is more readable as one block
    )

    @classmethod
    def _signature(cls, knowledge_base) -> str:
        return (
            f"{knowledge_base.id}:"
            f"{knowledge_base.total_documents}:"
            f"{knowledge_base.total_chunks}:"
            f"{knowledge_base.updated_at}"
        )

    @classmethod
    def _load_vocabulary(cls, knowledge_base) -> list[str]:
        from django.db import connection

        sql = r"""
            SELECT word, COUNT(*) AS cnt
            FROM (
                SELECT regexp_replace(
                    lower(unnest(string_to_array(dc.content, E' '))),
                    '[^a-z0-9]', '', 'g'
                ) AS word
                FROM documents_documentchunk dc
                JOIN documents_document d ON dc.document_id = d.id
                JOIN knowledge_knowledgebase kb ON d.knowledge_base_id = kb.id
                WHERE kb.id = %s
                  AND d.is_deleted = false
                  AND d.status = 'completed'
                UNION ALL
                SELECT regexp_replace(
                    lower(unnest(string_to_array(
                        qp.question || ' ' || qp.answer, E' '))),
                    '[^a-z0-9]', '', 'g'
                ) AS word
                FROM knowledge_qapair qp
                WHERE qp.knowledge_base_id = %s
                  AND qp.is_active = true
            ) words
            WHERE word <> ''
            GROUP BY word
            ORDER BY cnt DESC
            LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [knowledge_base.id, knowledge_base.id, cls.MAX_VOCAB_WORDS])
            rows = cursor.fetchall()
        words = [row[0] for row in rows if row[0]]
        # Prefer meaningful (longer) terms when breaking ties
        words.sort(key=len, reverse=True)
        return words

    @classmethod
    def get_vocabulary(cls, knowledge_base) -> frozenset:
        signature = cls._signature(knowledge_base)
        cached = cls._vocab_cache.get(str(knowledge_base.id))
        if cached and cached[0] == signature:
            return cached[1]
        vocab = frozenset(cls.COMMON_WORDS) | frozenset(cls._load_vocabulary(knowledge_base))
        if len(cls._vocab_cache) > 100:
            cls._vocab_cache.clear()
        cls._vocab_cache[str(knowledge_base.id)] = (signature, vocab)
        return vocab

    @classmethod
    def correct(cls, question: str, knowledge_base) -> str:
        """Correct unknown words in ``question`` against the KB vocabulary."""
        if not question or knowledge_base is None:
            return question
        vocab = cls.get_vocabulary(knowledge_base)
        if not vocab:
            return question

        spell = _get_spellchecker()
        domain_vocab = list(vocab - set(cls.COMMON_WORDS))

        import re

        tokens = re.findall(r"\S+", question)
        corrected = []
        for token in tokens:
            core_match = re.search(r"[A-Za-z]+", token)
            if not core_match:
                corrected.append(token)
                continue
            core = core_match.group(0).lower()
            if (
                len(core) < cls.MIN_WORD_LENGTH
                or core in vocab
                or spell.known([core])
            ):
                corrected.append(token)
                continue

            replacement = _levenshtein_best_match(core, domain_vocab, cls.DOMAIN_MATCH_CUTOFF)
            if replacement is None:
                english = spell.correction(core)
                if (
                    english
                    and english != core
                    and _levenshtein(core, english) <= cls.MAX_ENGLISH_EDIT_DISTANCE
                ):
                    replacement = english

            if replacement is None:
                corrected.append(token)
                continue

            original_start = token[core_match.start() : core_match.start() + 1]
            if original_start.isupper():
                replacement = replacement.capitalize()
            corrected.append(
                token[: core_match.start()] + replacement + token[core_match.end() :]
            )
            logger.info("Corrected '%s' -> '%s' in query: %s", core, replacement, question)

        return " ".join(corrected)


class EmbeddingService:
    """
    Service for generating embeddings using local models.

    Supports multiple embedding models with caching to avoid
    reloading models on each request.
    """

    QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

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

        # When a local model directory is configured (fully offline
        # deployment), load the default BGE model straight from disk.
        if (
            settings.EMBEDDING_MODEL_DIR
            and model_name == settings.DEFAULT_EMBEDDING_MODEL
        ):
            model_name = settings.EMBEDDING_MODEL_DIR

        if model_name not in _model_cache:
            logger.info(f"Loading embedding model: {model_name}")
            try:
                from sentence_transformers import SentenceTransformer

                _model_cache[model_name] = SentenceTransformer(model_name, device="cpu")
                logger.info(f"Successfully loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                raise

        return _model_cache[model_name]

    @staticmethod
    def generate_embedding(
        text: str,
        model_name: str = None,
        is_query: bool = False,
    ) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for.
            model_name: Name of the model to use.
            is_query: Whether this text is a retrieval query rather than a
                passage. BGE models require a query instruction prefix to
                align queries with indexed passages.

        Returns:
            List of floats representing the embedding.
        """
        model = EmbeddingService.get_model(model_name)
        if is_query and "bge" in (model_name or settings.DEFAULT_EMBEDDING_MODEL).lower():
            text = f"{EmbeddingService.QUERY_INSTRUCTION}{text}"
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

    CHUNK_SIMILARITY_THRESHOLD = 0.5
    QA_SIMILARITY_THRESHOLD = 0.5

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
                dc.document_id,
                dc.content,
                dc.chunk_index,
                dc.page_number,
                dc.metadata,
                d.title as document_title,
                1 - (dc.embedding <=> %s::vector) as similarity
            FROM documents_documentchunk dc
            JOIN documents_document d ON dc.document_id = d.id
            JOIN knowledge_knowledgebase kb ON d.knowledge_base_id = kb.id
            WHERE
                kb.chatbot_id = %s
                AND d.is_deleted = false
                AND d.status = 'completed'
                AND dc.embedding IS NOT NULL
                AND 1 - (dc.embedding <=> %s::vector) >= %s
            ORDER BY dc.embedding <=> %s::vector
            LIMIT %s
        """

        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [embedding_str, chatbot_id, embedding_str, similarity_threshold, embedding_str, top_k],
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return results

    @staticmethod
    def search_qa_pairs(
        query_embedding: list[float],
        knowledge_base_id: str,
        top_k: int = 3,
        similarity_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Search for similar Q&A pairs.

        Args:
            query_embedding: The query embedding vector.
            knowledge_base_id: The knowledge base ID.
            top_k: Number of results to return.
            similarity_threshold: Minimum cosine similarity to include a pair.

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
                AND 1 - (qp.embedding <=> %s::vector) >= %s
            ORDER BY qp.embedding <=> %s::vector
            LIMIT %s
        """

        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [embedding_str, knowledge_base_id, embedding_str, similarity_threshold, embedding_str, top_k],
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return results

    @staticmethod
    def expand_chunks(
        chunks: list[dict[str, Any]],
        surround: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Expand seed chunks with the chunks surrounding them in the same
        document.

        A retrieval hit is often a single line or fragment inside a larger
        module. This pulls the ``surround`` chunks before and after each
        seed so the whole section is available as context instead of just
        the one matching line. Neighbors carry no similarity score.

        Args:
            chunks: Seed chunks from :meth:`search_similar_chunks`.
            surround: How many chunks to include before/after each seed.

        Returns:
            Seed and neighbor chunks merged in document+index order.
        """
        if not chunks:
            return chunks

        from django.db import connection

        seed_by_key = {
            (chunk["document_id"], chunk["chunk_index"]): chunk
            for chunk in chunks
            if chunk.get("document_id") is not None
        }

        neighbor_by_key: dict[tuple, dict[str, Any]] = {}
        with connection.cursor() as cursor:
            for seed in sorted(
                chunks,
                key=lambda c: c.get("similarity") or 0,
                reverse=True,
            ):
                doc_id = seed.get("document_id")
                chunk_index = seed.get("chunk_index")
                if doc_id is None or chunk_index is None:
                    continue
                cursor.execute(
                    """
                    SELECT
                        dc.id,
                        dc.document_id,
                        dc.content,
                        dc.chunk_index,
                        dc.page_number,
                        dc.metadata,
                        d.title as document_title
                    FROM documents_documentchunk dc
                    JOIN documents_document d ON dc.document_id = d.id
                    WHERE
                        dc.document_id = %s
                        AND dc.chunk_index BETWEEN %s AND %s
                        AND d.is_deleted = false
                        AND d.status = 'completed'
                    ORDER BY dc.chunk_index ASC
                    """,
                    [
                        doc_id,
                        max(0, chunk_index - surround),
                        chunk_index + surround,
                    ],
                )
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    key = (item["document_id"], item["chunk_index"])
                    if key not in seed_by_key:
                        item["similarity"] = None
                        neighbor_by_key[key] = item

        merged = list(seed_by_key.values())
        merged.extend(neighbor_by_key.values())
        merged.sort(key=lambda c: (c.get("document_title", ""), c.get("chunk_index", 0)))
        return merged


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
        messages: list[dict],
        model: str = None,
        temperature: float = 0.2,
        top_p: float = 0.5,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        num_ctx: int = None,
        stream: bool = False,
    ) -> str:
        """
        Generate a response using Ollama's chat endpoint.

        Uses ``/api/chat`` with a proper message list so the model's
        native chat template (e.g. Llama 3.2) is applied.

        Args:
            messages: List of chat messages with ``role`` and ``content``.
            model: The model to use.
            temperature: Temperature for generation.
            top_p: Top P for generation.
            max_tokens: Maximum tokens to generate.
            num_ctx: Context window size for the model.
            stream: Whether to stream the response.

        Returns:
            Generated response string.
        """
        import requests as http_requests

        if model is None:
            model = settings.DEFAULT_LLM

        url = f"{self.base_url}/api/chat"

        options = {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        }
        if num_ctx:
            options["num_ctx"] = num_ctx

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options,
        }

        try:
            response = http_requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json().get("message", {}).get("content", "")

        except http_requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise
        except http_requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def _handle_stream_response(self, response) -> str:
        """Handle streaming response from Ollama chat endpoint."""
        full_response = []
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                message = chunk.get("message", {})
                content = message.get("content", "")
                if content:
                    full_response.append(content)
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
        # Correct typos in the question against the knowledge base vocabulary
        question = QueryCorrector.correct(question, chatbot.knowledge_base)

        # Generate question embedding
        question_embedding = self.embedding_service.generate_embedding(
            question,
            model_name=chatbot.embedding_model,
            is_query=True,
        )

        # Search for similar chunks
        similar_chunks = self.search_service.search_similar_chunks(
            query_embedding=question_embedding,
            chatbot_id=str(chatbot.id),
            top_k=chatbot.top_k,
        )

        # Expand seeds with surrounding chunks so whole modules are included
        if similar_chunks:
            similar_chunks = self.search_service.expand_chunks(similar_chunks)

        # Also search Q&A pairs
        qa_pairs = []
        if chatbot.knowledge_base:
            qa_pairs = self.search_service.search_qa_pairs(
                query_embedding=question_embedding,
                knowledge_base_id=str(chatbot.knowledge_base.id),
                top_k=3,
                similarity_threshold=self.search_service.QA_SIMILARITY_THRESHOLD,
            )

        # Build context
        context = self._build_context(similar_chunks, qa_pairs)

        # Build chat messages (budgeted to the chatbot's context window)
        messages = self._build_messages(
            question=question,
            context=context,
            system_prompt=chatbot.system_prompt,
            conversation_history=conversation_history,
            max_context_tokens=chatbot.max_context_length,
        )

        # Generate answer
        answer = self.llm_service.generate(
            messages=messages,
            model=chatbot.llm_model,
            temperature=chatbot.temperature,
            top_p=chatbot.top_p,
            max_tokens=DEFAULT_MAX_TOKENS,
            num_ctx=max(4096, chatbot.max_context_length + DEFAULT_MAX_TOKENS),
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

        # Add document chunks (expanded chunks arrive grouped by document
        # and in chunk order, so the module reads sequentially)
        if chunks:
            context_parts.append("Relevant information from knowledge base:")
            current_source = None
            for chunk in chunks:
                source = chunk.get("document_title", "Unknown")
                content = chunk.get("content", "")
                if not content:
                    continue
                if source != current_source:
                    context_parts.append(f"\n===== {source} =====")
                    current_source = source
                similarity = chunk.get("similarity")
                relevance = (
                    f" (Relevance: {similarity:.2f})" if similarity is not None else ""
                )
                context_parts.append(f"\n{content}{relevance}")

        # Add Q&A pairs
        if qa_pairs:
            context_parts.append("\n\nRelevant Q&A from knowledge base:")
            for qa in qa_pairs:
                context_parts.append(
                    f"\nQ: {qa['question']}\nA: {qa['answer']}"
                )

        return "\n".join(context_parts) if context_parts else "No relevant information found."

    def _build_messages(
        self,
        question: str,
        context: str,
        system_prompt: str,
        conversation_history: list[dict] = None,
        max_context_tokens: int = 4096,
    ) -> list[dict]:
        """
        Build a chat message list for the LLM.

        Budgets history and retrieved context to stay within
        ``max_context_tokens`` so nothing is silently truncated by the
        model's context window. Most relevant (first) context is kept.

        Args:
            question: The user's question.
            context: The context from the knowledge base.
            system_prompt: The chatbot's system prompt.
            conversation_history: Optional conversation history.
            max_context_tokens: Maximum input tokens for the model.

        Returns:
            List of chat messages.
        """
        instruction = (
            "Use ONLY the provided context to answer the question. "
            "If the answer is not in the context, say "
            "'I don't know based on the provided knowledge.' "
            "Do not make up information or hallucinate."
        )

        system_tokens = estimate_tokens(system_prompt)
        question_tokens = estimate_tokens(question)
        instruction_tokens = estimate_tokens(instruction)

        # Reserve a third of the budget for conversation history so it
        # can't starve the retrieved context.
        history_budget = max(
            0,
            (max_context_tokens - system_tokens - question_tokens - instruction_tokens) // 3,
        )

        history_messages = []
        if conversation_history and history_budget > 0:
            used = 0
            for msg in reversed(conversation_history[-5:]):
                content = msg.get("content", "")
                role = msg.get("role", "user")
                role = "assistant" if str(role).lower() == "assistant" else "user"
                msg_tokens = estimate_tokens(content)
                if used + msg_tokens > history_budget:
                    break
                history_messages.append({"role": role, "content": content})
                used += msg_tokens
            history_messages.reverse()

        history_tokens = sum(estimate_tokens(m["content"]) for m in history_messages)
        context_budget = max(
            1,
            max_context_tokens
            - system_tokens
            - question_tokens
            - instruction_tokens
            - history_tokens,
        )
        budgeted_context = truncate_to_tokens(context, context_budget)

        user_content = (
            f"Context from knowledge base:\n{budgeted_context}\n\n"
            f"Question: {question}\n\n{instruction}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": user_content})
        return messages


def stream_chat_response(
    conversation,
    chatbot,
    message_content: str,
    conversation_history: list[dict] = None,
    no_content_message: str = (
        "This chatbot does not have any documents or Q&A pairs in its knowledge base. "
        "Please add content before chatting."
    ),
):
    """
    Generator yielding SSE-encoded events for a streaming chat response.

    Yields raw ``data: {...}\\n\\n`` lines (token / done / error events) so any
    caller can wrap them in a StreamingHttpResponse. Reuses the RAG pipeline for
    retrieval and Ollama for token generation, persists the assistant message,
    and updates conversation/chatbot usage stats.

    Args:
        conversation: The Conversation instance to append messages to.
        chatbot: The Chatbot instance answering the message.
        message_content: The user's message text.
        conversation_history: Prior messages to include as context.
        no_content_message: Message sent when the knowledge base is empty.
    """
    from apps.chat.models import Message

    # Check if chatbot has documents or QA pairs in its knowledge base
    kb = chatbot.knowledge_base
    has_content = kb and (
        kb.total_documents > 0
        or kb.qa_pairs.filter(is_active=True).exists()
    )

    if not has_content:
        yield f"data: {json.dumps({'token': no_content_message})}\n\n"
        yield f"data: {json.dumps({'done': True, 'conversation_id': str(conversation.id)})}\n\n"
        return

    try:
        # Correct typos in the message against the knowledge base vocabulary
        question = QueryCorrector.correct(message_content, chatbot.knowledge_base)

        embedding_service = EmbeddingService()
        search_service = VectorSearchService()

        question_embedding = embedding_service.generate_embedding(
            question,
            model_name=chatbot.embedding_model,
            is_query=True,
        )

        similar_chunks = search_service.search_similar_chunks(
            query_embedding=question_embedding,
            chatbot_id=str(chatbot.id),
            top_k=chatbot.top_k,
        )

        # Expand seeds with surrounding chunks so whole modules are included
        if similar_chunks:
            similar_chunks = search_service.expand_chunks(similar_chunks)

        # Also search Q&A pairs
        qa_pairs = []
        if chatbot.knowledge_base:
            qa_pairs = search_service.search_qa_pairs(
                query_embedding=question_embedding,
                knowledge_base_id=str(chatbot.knowledge_base.id),
                top_k=3,
                similarity_threshold=search_service.QA_SIMILARITY_THRESHOLD,
            )

        # Build context
        rag = RAGPipeline()
        context = rag._build_context(similar_chunks, qa_pairs)

        # Build chat messages (budgeted to the chatbot's context window)
        messages = rag._build_messages(
            question=question,
            context=context,
            system_prompt=chatbot.system_prompt,
            conversation_history=conversation_history,
            max_context_tokens=chatbot.max_context_length,
        )

        # Stream response from Ollama
        ollama = OllamaService()
        full_response = []

        url = f"{ollama.base_url}/api/chat"
        payload = {
            "model": chatbot.llm_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": chatbot.temperature,
                "top_p": chatbot.top_p,
                "num_predict": DEFAULT_MAX_TOKENS,
                "num_ctx": max(4096, chatbot.max_context_length + DEFAULT_MAX_TOKENS),
            },
        }

        import requests

        response = requests.post(url, json=payload, stream=True, timeout=120)

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

        # Save complete response
        complete_response = "".join(full_response)
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=complete_response,
            metadata={
                "sources": [
                    {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in s.items()}
                    for s in similar_chunks
                ],
                "model_used": chatbot.llm_model,
            },
        )

        # Update stats
        conversation.message_count = conversation.messages.count()
        conversation.last_message_at = assistant_message.created_at
        conversation.save(update_fields=["message_count", "last_message_at"])
        chatbot.update_usage_stats()

        # Send completion event
        yield f"data: {json.dumps({'done': True, 'conversation_id': str(conversation.id)})}\n\n"

    except Exception as e:
        logger.error("Error streaming chat response: %s", e)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
