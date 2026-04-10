from django.urls import path
from . import views

urlpatterns = [
    path("start", views.NewPlayerView.as_view(), name="start-game"),
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
    path("stations/visited/", views.VisitedStationsView.as_view(),
         name="visited-stations"),
    path("stations/<str:station_id>/enter/",
         views.enter_station_view, name="station-enter"),
    path("stations/<str:station_id>/run/",
         views.run_station_view, name="station-run"),
]
