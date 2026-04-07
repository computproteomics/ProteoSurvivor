from django.urls import path
from . import views

urlpatterns = [
    path("levels/", views.LevelListView.as_view(), name="level-list"),
    path("levels/<int:pk>/dataset/", views.LevelDatasetView.as_view(), name="level-dataset"),
    path("sessions/", views.GameSessionCreateView.as_view(), name="session-create"),
    path("sessions/<int:pk>/submit/", views.submit_answer, name="session-submit"),
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
]
