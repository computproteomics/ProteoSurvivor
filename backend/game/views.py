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
    """POST /api/stations/<station_id>/run/ — run a proteomics station with given parameters."""
    if station_id not in settings.STATIONS_CONFIG:
        return Response(
            {"detail": f"Unknown station '{station_id}'."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = RunStationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    station_run = run_station(request,
        station_id=station_id,
        params=serializer.validated_data["params"],
    )
    return Response(RunStationSerializer(station_run).data, status=status.HTTP_201_CREATED)
