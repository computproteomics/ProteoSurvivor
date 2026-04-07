from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Level, GameSession, Score
from .serializers import (
    LevelSerializer,
    GameSessionSerializer,
    ScoreSerializer,
    SubmitAnswerSerializer,
    LeaderboardEntrySerializer,
    RunStationSerializer,
    StationRunSerializer,
)
from .services import evaluate_answer, run_station
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
    return Response(ScoreSerializer(score).data, status=status.HTTP_201_CREATED)


class LeaderboardView(generics.ListAPIView):
    """GET /api/leaderboard/ — top scores across all levels."""

    queryset = Score.objects.select_related("session__player", "session__level").order_by(
        "-points", "time_taken_seconds"
    )[:50]
    serializer_class = LeaderboardEntrySerializer


VALID_STATION_IDS = {"sample_prep", "mass_spec", "search_setup", "data_analysis", "veit"}


@api_view(["POST"])
def run_station_view(request, station_id):
    """POST /api/stations/<station_id>/run/ — run a proteomics station with given parameters."""
    if station_id not in VALID_STATION_IDS:
        return Response(
            {"detail": f"Unknown station '{station_id}'."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = RunStationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    player = request.user if request.user.is_authenticated else None
    station_run = run_station(
        station_id=station_id,
        params=serializer.validated_data["params"],
        player=player,
    )
    return Response(StationRunSerializer(station_run).data, status=status.HTTP_201_CREATED)
