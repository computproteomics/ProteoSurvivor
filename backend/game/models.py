from django.db import models
from django.contrib.auth.models import User


class StationRun(models.Model):
    """Records one execution of a proteomics lab station with its parameters and results."""

    player = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="station_runs"
    )
    station_id = models.CharField(
        max_length=50,
        help_text="Identifier for the station, e.g. 'sample_prep', 'mass_spec', etc.",
    )
    params = models.JSONField(default=dict)
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"StationRun {self.pk} by {self.player} at {self.created_at}"


class CutterStationResult(models.Model):
    """Stores the results of a cutter station run, including the generated peptides."""

    station_run = models.OneToOneField(
        StationRun, on_delete=models.CASCADE, related_name="cutter_result"
    )
    true_positives = models.PositiveIntegerField()
    false_positives = models.PositiveIntegerField()

    def __str__(self):
        return f"CutterStationResult for StationRun {self.station_run.pk}"