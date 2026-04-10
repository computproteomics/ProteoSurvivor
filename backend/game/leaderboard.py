from typing import Any

from django.contrib.auth.models import User
from django.db.models import OuterRef, Subquery

from .models import StationRun


def get_user_game_result(user: User) -> dict[str, Any]:
    latest_run = user.station_runs.order_by("-created_at", "-pk").first()
    if latest_run is None:
        return {"last_station_id": None, "score": None}

    return {
        "last_station_id": latest_run.station_id,
        "score": latest_run.score,
    }


def get_leaderboard_information() -> list[dict[str, Any]]:
    latest_runs = StationRun.objects.filter(player=OuterRef("pk")).order_by("-created_at", "-pk")

    users = User.objects.annotate(
        last_station_id=Subquery(latest_runs.values("station_id")[:1]),
        latest_score=Subquery(latest_runs.values("score")[:1]),
    ).values("username", "first_name", "last_station_id", "latest_score")

    leaderboard = []
    for user in users:
        last_station_id = user["last_station_id"]
        leaderboard.append(
            {
                "user_id": user["username"],
                "user_name": user["first_name"] or user["username"],
                "last_station_id": last_station_id,
                "score": user["latest_score"],
                "status": "finished" if last_station_id == "veit" else "DNF",
            }
        )

    return leaderboard