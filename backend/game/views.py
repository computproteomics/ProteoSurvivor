from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.conf import settings
from .serializers import (
    RunStationSerializer,
)
from .services import run_station


@api_view(["POST"])
def run_station_view(request, station_id):
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"success": False, "feedback": f"Unknown station '{station_id}'.", "score": None},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = RunStationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "feedback": "Invalid request payload.", "score": None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = run_station(
            request,
            station_id=station_id,
            params=serializer.validated_data["params"],
        )
    except Exception:
        return Response(
            {"success": False, "feedback": "Station execution failed.", "score": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "success": bool(result.get("success", False)),
            "feedback": result.get("feedback", "Station completed."),
            "score": result.get("score", None),
        },
        status=status.HTTP_200_OK,
    )
