from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view
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
from .services import run_station


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
def enter_station_view(request, station_id):
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"detail": f"Unknown station '{station_id}'."},
            status=status.HTTP_404_NOT_FOUND,
        )

    request.session["current_station"] = station_id
    return Response(
        {
            "message": f"Entered station '{station_id}' successfully.",
            "station_id": station_id,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def run_station_view(request, station_id):
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"success": False, "feedback": f"Unknown station '{station_id}'.", "score": None},
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
