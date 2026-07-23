"""
API Views for HelpDesk-AI.
REST API endpoints for authentication, chatbots, documents, knowledge, and chat.
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.chatbots.models import Chatbot
from apps.chatbots.selectors import get_user_chatbots
from apps.chatbots.serializers import (
    ChatbotCreateSerializer,
    ChatbotListSerializer,
    ChatbotSerializer,
    ChatbotUpdateSerializer,
)

User = get_user_model()


# ==================== Authentication API ====================


class RegisterAPIView(generics.CreateAPIView):
    """
    API view for user registration.
    """

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        """Create a new user and return token."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """
    API view for user login.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Authenticate user and return token."""
        from django.contrib.auth import authenticate

        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "token": token.key,
                }
            )
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class LogoutAPIView(APIView):
    """
    API view for user logout.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Delete user's auth token."""
        try:
            request.user.auth_token.delete()
        except (Token.DoesNotExist, AttributeError):
            pass
        return Response({"message": "Logged out successfully"})


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    API view for user profile.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current user."""
        return self.request.user


class ChangePasswordAPIView(generics.UpdateAPIView):
    """
    API view for changing password.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current user."""
        return self.request.user

    def update(self, request, *args, **kwargs):
        """Update the password."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password changed successfully"})


# ==================== Chatbot API ====================


class ChatbotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Chatbot CRUD operations.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatbotSerializer

    def get_queryset(self):
        """Return chatbots for the current user."""
        return get_user_chatbots(self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return ChatbotCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ChatbotUpdateSerializer
        elif self.action == "list":
            return ChatbotListSerializer
        return ChatbotSerializer

    def perform_create(self, serializer):
        """Set the owner to the current user."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """Toggle chatbot active status."""
        chatbot = self.get_object()
        if chatbot.is_active:
            chatbot.deactivate()
        else:
            chatbot.activate()
        return Response(ChatbotSerializer(chatbot).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a chatbot."""
        from apps.chatbots.services import ChatbotService

        original = self.get_object()
        new_chatbot = ChatbotService.duplicate_chatbot(original)
        return Response(
            ChatbotSerializer(new_chatbot).data,
            status=status.HTTP_201_CREATED,
        )


# ==================== Document API ====================


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document operations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return documents for the user's chatbots."""
        from apps.documents.models import Document

        return Document.objects.filter(
            knowledge_base__chatbot__owner=self.request.user,
            is_deleted=False,
        )

    def get_serializer_class(self):
        """Return appropriate serializer."""
        from apps.documents.serializers import DocumentSerializer

        return DocumentSerializer

    def perform_create(self, serializer):
        """Create document and trigger processing."""
        document = serializer.save()
        # Trigger async processing
        from apps.documents.tasks import process_document_task

        process_document_task.delay(str(document.id))


# ==================== Knowledge Base API ====================


class KnowledgeBaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Knowledge Base read operations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return knowledge bases for the user's chatbots."""
        from apps.knowledge.models import KnowledgeBase

        return KnowledgeBase.objects.filter(
            chatbot__owner=self.request.user,
        )

    def get_serializer_class(self):
        """Return appropriate serializer."""
        from apps.knowledge.serializers import KnowledgeBaseSerializer

        return KnowledgeBaseSerializer


# ==================== Chat API ====================


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Conversation operations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return conversations for the user."""
        from apps.chat.models import Conversation

        return Conversation.objects.filter(
            chatbot__owner=self.request.user,
        )

    def get_serializer_class(self):
        """Return appropriate serializer."""
        from apps.chat.serializers import ConversationSerializer

        return ConversationSerializer


class ChatAPIView(APIView):
    """
    API view for sending chat messages.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Send a message and get a response."""
        from apps.chat.serializers import MessageSerializer
        from apps.rag.services import RAGPipeline

        chatbot_id = request.data.get("chatbot_id")
        message = request.data.get("message")
        conversation_id = request.data.get("conversation_id")

        if not chatbot_id or not message:
            return Response(
                {"error": "chatbot_id and message are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get chatbot
        chatbot = get_object_or_404(
            Chatbot,
            id=chatbot_id,
            owner=request.user,
        )

        # Get or create conversation
        from apps.chat.models import Conversation

        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id,
                chatbot=chatbot,
            )
        else:
            import uuid

            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user=request.user,
                title=message[:50],
                session_id=str(uuid.uuid4()),
            )

        # Create user message
        from apps.chat.models import Message

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message,
        )

        # Get conversation history
        conversation_history = list(
            conversation.messages.values("role", "content")[:10]
        )

        # Generate response using RAG
        rag_pipeline = RAGPipeline()
        result = rag_pipeline.answer_question(
            question=message,
            chatbot=chatbot,
            conversation_history=conversation_history[:-1],
        )

        # Create assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=result["answer"],
            metadata={
                "sources": result["sources"],
                "model_used": result["model_used"],
            },
        )

        # Update chatbot usage
        chatbot.update_usage_stats()

        return Response(
            {
                "conversation_id": str(conversation.id),
                "message": MessageSerializer(assistant_message).data,
            }
        )


# ==================== Health Check API ====================


class HealthCheckAPIView(APIView):
    """
    API view for health check.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Return health status."""
        return Response(
            {
                "status": "healthy",
                "version": "1.0.0",
            }
        )
