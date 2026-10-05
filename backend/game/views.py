from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import cast

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from .serializers import (
    NewPlayerSerializer,
    RunStationSerializer,
)
from .leaderboard import get_leaderboard_information
from .helper_functions import plot_scores, get_visited_stations
from .services import RerunNotAllowed, run_station


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication that skips CSRF enforcement.

    DRF's default SessionAuthentication enforces CSRF for every authenticated
    session.  When the CSRF cookie is absent (e.g. the browser was restarted
    and only the longer-lived session cookie survived), any POST to a station
    endpoint returns 403 before the view logic can run.

    The station endpoints are already protected by CORS in production and by
    the game session (users must have called /api/start first).  Skipping the
    additional CSRF layer here removes the false-403 while keeping session-
    based user identification intact.
    """

    def enforce_csrf(self, request):
        return None  # intentionally skipped for API endpoints


def _build_unique_user_id(base_name: str) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in base_name).strip("_")
    base = base[:120] or "player"

    suffix = 1
    candidate = base
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base}_{suffix}"
    return candidate


class NewPlayerView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NewPlayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict, serializer.validated_data)

        user_name = str(validated_data["user_name"]).strip()
        username = _build_unique_user_id(user_name)
        user = User.objects.create_user(
            username=username,
            password=User.objects.make_random_password(),
            first_name=user_name,
        )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.save()
        get_token(request)

        return Response(
            {
                "user_id": user.username,
                "user_name": user.first_name or user.username,
                "session_id": request.session.session_key,
                "created": True,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def enter_station_view(request, station_id):
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"detail": f"Unknown station '{station_id}'."},
            status=status.HTTP_404_NOT_FOUND,
        )

    station_config = settings.STATIONS_CONFIG[station_id]
    visited_stations = get_visited_stations(request.user)
    for requirement in station_config.get("requires", []):
        required_station_id = requirement.get("id")
        if required_station_id and required_station_id not in visited_stations:
            return Response(
                {
                    "success": False,
                    "feedback": requirement.get(
                        "message",
                        f"Station '{required_station_id}' must be completed first.",
                    ),
                    "missing_station_id": required_station_id,
                    "station_id": station_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    request.session["current_station"] = station_id
    # Entering a station fresh means an earlier run can no longer be adjusted.
    request.session.pop("last_saved_run", None)
    return Response(
        {
            "success": True,
            "message": f"",
            "station_id": station_id,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def run_station_view(request, station_id):
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"success": False, "feedback": f"Unknown station '{station_id}'.", "score": 0},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = RunStationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    validated_data = cast(dict, serializer.validated_data)

    result = run_station(request,
        station_id=station_id,
        params=validated_data["params"],
    )
    return Response(result, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])  # enforces CSRF
@permission_classes([IsAuthenticated])
def rerun_station_view(request, station_id):
    """"Adjust parameters": re-run the last saved run of a station and update it in place."""
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"success": False, "feedback": f"Unknown station '{station_id}'.", "score": 0},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = RunStationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    validated_data = cast(dict, serializer.validated_data)

    try:
        result = run_station(
            request,
            station_id=station_id,
            params=validated_data["params"],
            rerun=True,
        )
    except RerunNotAllowed as exc:
        return Response(
            {"success": False, "feedback": str(exc), "score": 0},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(result, status=status.HTTP_200_OK)


class LeaderboardView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def _score_sort_key(entry: dict) -> tuple[float, str]:
        score = entry.get("score")
        safe_score = float(score) if score is not None else float("-inf")
        return (safe_score, str(entry.get("user_name", "")))

    def get(self, request):
        leaderboard = get_leaderboard_information()

        finished = sorted(
            (entry for entry in leaderboard if entry["status"] == "finished"),
            key=self._score_sort_key,
            reverse=True,
        )[:10]
        dnf = sorted(
            (entry for entry in leaderboard if entry["status"] == "DNF"),
            key=self._score_sort_key,
            reverse=True,
        )[:10]

        current_user_result = None
        if request.user.is_authenticated:
            current_user_result = next(
                (entry for entry in leaderboard if entry["user_id"] == request.user.username),
                None,
            )

        return Response(
            {
                "finished": finished,
                "dnf": dnf,
                "current_user_result": current_user_result,
            },
            status=status.HTTP_200_OK,
        )


class ScatterPlotView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "img": plot_scores(),
            },
            status=status.HTTP_200_OK,
        )
