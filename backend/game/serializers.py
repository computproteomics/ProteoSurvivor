import base64
import pickle

from rest_framework import serializers


class DataFrameSessionSerializer:
    """Encode/decode a pandas DataFrame for storage in Django's JSON session."""

    @staticmethod
    def dumps(df) -> str:
        return base64.b64encode(pickle.dumps(df)).decode("ascii")

    @staticmethod
    def loads(value: str):
        return pickle.loads(base64.b64decode(value))


class NewPlayerSerializer(serializers.Serializer):
    user_name = serializers.CharField(max_length=64)


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
