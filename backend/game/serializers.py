from rest_framework import serializers
from .models import Level, GameSession, Score, StationRun


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ["id", "title", "description", "challenge_type", "difficulty"]


class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ["id", "points", "time_taken_seconds", "feedback", "created_at"]


class GameSessionSerializer(serializers.ModelSerializer):
    score = ScoreSerializer(read_only=True)
    level = LevelSerializer(read_only=True)
    level_id = serializers.PrimaryKeyRelatedField(
        queryset=Level.objects.all(), source="level", write_only=True
    )

    class Meta:
        model = GameSession
        fields = ["id", "level", "level_id", "status", "started_at", "completed_at", "score"]
        read_only_fields = ["status", "started_at", "completed_at"]


class SubmitAnswerSerializer(serializers.Serializer):
    answer = serializers.JSONField()
    time_taken_seconds = serializers.IntegerField(min_value=0)


class RunStationSerializer(serializers.Serializer):
    params = serializers.JSONField()


class StationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationRun
        fields = ["id", "station_id", "params", "results", "status", "created_at"]


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    level_title = serializers.CharField(source="session.level.title", read_only=True)

    class Meta:
        model = Score
        fields = ["id", "player_name", "level_title", "points", "time_taken_seconds", "created_at"]

    def get_player_name(self, obj):
        if obj.session.player:
            return obj.session.player.username
        return "Anonymous"
