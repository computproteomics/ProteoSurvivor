from django.db import models


class Dataset(models.Model):
    """A named dataset that can be associated with one or more levels."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    raw_data = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Challenge(models.Model):
    """Links a Dataset to a Level and stores the ground-truth answer."""

    level = models.ForeignKey(
        "game.Level", on_delete=models.CASCADE, related_name="challenges"
    )
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="challenges")
    answer_key = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Challenge: {self.level} <-> {self.dataset}"
