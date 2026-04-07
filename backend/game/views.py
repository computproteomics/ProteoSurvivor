from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Level, GameSession, Score
from .serializers import (
    LevelSerializer,
    GameSessionSerializer,
    SubmitAnswerSerializer,
    LeaderboardEntrySerializer,
)
from .services import evaluate_answer
from data.generators import generate_dataset_for_level


class LevelListView(generics.ListAPIView):
    """GET /api/levels/ — list active levels."""

    queryset = Level.objects.filter(is_active=True)
    serializer_class = LevelSerializer


class LevelDatasetView(generics.RetrieveAPIView):
    """GET /api/levels/{id}/dataset/ — return a synthetic dataset for the level."""

    queryset = Level.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        level = self.get_object()
        dataset = generate_dataset_for_level(level)
        return Response(dataset)


class GameSessionCreateView(generics.CreateAPIView):
    """POST /api/sessions/ — start a new game session."""

    serializer_class = GameSessionSerializer

    def perform_create(self, serializer):
        player = self.request.user if self.request.user.is_authenticated else None
        serializer.save(player=player)


@api_view(["POST"])
def submit_answer(request, pk):
    """POST /api/sessions/{id}/submit/ — submit answer and receive score."""
    try:
        session = GameSession.objects.get(pk=pk, status="in_progress")
    except GameSession.DoesNotExist:
        return Response(
            {"detail": "Session not found or already completed."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = SubmitAnswerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    score = evaluate_answer(
        session,
        serializer.validated_data["answer"],
        serializer.validated_data["time_taken_seconds"],
    )
    from .serializers import ScoreSerializer

    return Response(ScoreSerializer(score).data, status=status.HTTP_201_CREATED)


class LeaderboardView(generics.ListAPIView):
    """GET /api/leaderboard/ — top scores across all levels."""

    queryset = Score.objects.select_related("session__player", "session__level").order_by(
        "-points", "time_taken_seconds"
    )[:50]
    serializer_class = LeaderboardEntrySerializer
