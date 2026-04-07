"""
Game logic: scoring and answer evaluation per challenge type.
"""
import random
from django.utils import timezone
from .models import GameSession, Score


def evaluate_answer(session: GameSession, answer: dict, time_taken: int) -> Score:
    """
    Score the player's answer for the given session and persist a Score record.
    Returns the created Score instance.
    """
    level = session.level
    points, feedback = _score_by_type(level.challenge_type, answer, level.difficulty)

    session.status = "completed"
    session.completed_at = timezone.now()
    session.save(update_fields=["status", "completed_at"])

    score = Score.objects.create(
        session=session,
        points=points,
        time_taken_seconds=time_taken,
        answer_payload=answer,
        feedback=feedback,
    )
    return score


def _score_by_type(challenge_type: str, answer: dict, difficulty: int) -> tuple[int, str]:
    """Return (points, feedback_text) for a given challenge type."""
    handlers = {
        "outlier": _score_outlier,
        "correlation": _score_correlation,
        "clean": _score_clean,
        "trend": _score_trend,
    }
    handler = handlers.get(challenge_type, _score_default)
    return handler(answer, difficulty)


def _score_outlier(answer: dict, difficulty: int) -> tuple[int, str]:
    selected = answer.get("selected_indices", [])
    correct = answer.get("correct_indices", [])
    if not correct:
        return 0, "No correct answer provided."
    hits = len(set(selected) & set(correct))
    max_points = 100 * difficulty
    points = int((hits / len(correct)) * max_points) if correct else 0
    feedback = f"You identified {hits}/{len(correct)} outliers correctly."
    return points, feedback


def _score_correlation(answer: dict, difficulty: int) -> tuple[int, str]:
    chosen = answer.get("correlation_type", "")
    correct = answer.get("correct_correlation_type", "")
    if chosen == correct:
        points = 100 * difficulty
        feedback = "Correct! You identified the correlation type."
    else:
        points = 0
        feedback = f"Incorrect. The correct answer was '{correct}'."
    return points, feedback


def _score_clean(answer: dict, difficulty: int) -> tuple[int, str]:
    cleaned = answer.get("cleaned_rows", [])
    expected = answer.get("expected_rows", [])
    if not expected:
        return 0, "No expected result provided."
    correct_count = sum(1 for r in cleaned if r in expected)
    max_points = 100 * difficulty
    points = int((correct_count / len(expected)) * max_points)
    feedback = f"You correctly cleaned {correct_count}/{len(expected)} rows."
    return points, feedback


def _score_trend(answer: dict, difficulty: int) -> tuple[int, str]:
    chosen = answer.get("trend", "")
    correct = answer.get("correct_trend", "")
    if chosen == correct:
        points = 100 * difficulty
        feedback = "Correct! You identified the trend."
    else:
        points = 0
        feedback = f"Incorrect. The correct trend was '{correct}'."
    return points, feedback


def _score_default(answer: dict, difficulty: int) -> tuple[int, str]:
    return 50 * difficulty, "Answer recorded."
