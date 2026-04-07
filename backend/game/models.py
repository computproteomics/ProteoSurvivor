from django.db import models
from django.contrib.auth.models import User


class Level(models.Model):
    """Represents a single game level / challenge."""

    CHALLENGE_TYPES = [
        ("outlier", "Find the Outlier"),
        ("correlation", "Identify the Correlation"),
        ("clean", "Clean the Dirty Data"),
        ("trend", "Spot the Trend"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=50, choices=CHALLENGE_TYPES)
    difficulty = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["difficulty", "title"]

    def __str__(self):
        return f"{self.title} (difficulty {self.difficulty})"


class GameSession(models.Model):
    """Tracks a single play-through of a level."""

    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("abandoned", "Abandoned"),
    ]

    player = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions"
    )
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="sessions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.pk} — {self.level} [{self.status}]"


class StationRun(models.Model):
    """Records one execution of a proteomics lab station with its parameters and results."""

    STATION_CHOICES = [
        ("sample_prep", "Sample Preparation"),
        ("mass_spec", "Mass Spectrometer"),
        ("search_setup", "Search Engine Setup"),
        ("data_analysis", "Data Analysis"),
        ("veit", "Veit"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    player = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="station_runs"
    )
    station_id = models.CharField(max_length=50, choices=STATION_CHOICES)
    params = models.JSONField(default=dict)
    results = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"StationRun {self.pk} — {self.station_id} [{self.status}]"


class Score(models.Model):
    """Stores the result of a completed game session."""

    session = models.OneToOneField(GameSession, on_delete=models.CASCADE, related_name="score")
    points = models.PositiveIntegerField(default=0)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    answer_payload = models.JSONField(default=dict)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-points", "time_taken_seconds"]

    def __str__(self):
        return f"Score {self.points} pts — {self.session}"
