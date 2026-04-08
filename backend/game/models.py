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
