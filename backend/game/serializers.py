from rest_framework import serializers
from .models import StationRun


class RunStationSerializer(serializers.Serializer):
    params = serializers.JSONField()


# class LeaderboardEntrySerializer(serializers.ModelSerializer):
#     player_name = serializers.SerializerMethodField()
#     level_title = serializers.CharField(source="session.level.title", read_only=True)

#     class Meta:
#         model = Score
#         fields = ["id", "player_name", "level_title", "points", "time_taken_seconds", "created_at"]

#     def get_player_name(self, obj):
#         if obj.session.player:
#             return obj.session.player.username
#         return "Anonymous"
