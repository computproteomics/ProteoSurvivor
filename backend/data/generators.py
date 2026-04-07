"""
Synthetic dataset generators for each challenge type.
Uses numpy and faker to produce realistic-looking tabular data.
"""
import random
import numpy as np

try:
    from faker import Faker

    _faker = Faker()
except ImportError:
    _faker = None


def generate_dataset_for_level(level) -> dict:
    """
    Return a JSON-serialisable dict with:
      - columns: list of column names
      - rows: list of row dicts
      - metadata: challenge-specific hints / answer key
    """
    generators = {
        "outlier": _generate_outlier_dataset,
        "correlation": _generate_correlation_dataset,
        "clean": _generate_clean_dataset,
        "trend": _generate_trend_dataset,
    }
    generator = generators.get(level.challenge_type, _generate_outlier_dataset)
    return generator(difficulty=level.difficulty)


def _generate_outlier_dataset(difficulty: int = 1) -> dict:
    n_rows = 20 + difficulty * 10
    rng = np.random.default_rng()
    values = rng.normal(loc=50, scale=5, size=n_rows).tolist()

    # Inject outliers
    n_outliers = difficulty
    outlier_indices = random.sample(range(n_rows), n_outliers)
    for idx in outlier_indices:
        values[idx] = float(rng.choice([-1, 1])) * rng.uniform(80, 120)

    rows = [
        {"id": i + 1, "sample": f"S{i+1:03d}", "value": round(values[i], 2)}
        for i in range(n_rows)
    ]
    return {
        "columns": ["id", "sample", "value"],
        "rows": rows,
        "metadata": {
            "task": "Select the row(s) containing outliers.",
            "outlier_indices": outlier_indices,
        },
    }


def _generate_correlation_dataset(difficulty: int = 1) -> dict:
    n_rows = 30 + difficulty * 10
    rng = np.random.default_rng()
    x = rng.uniform(0, 100, n_rows)

    correlation_type = random.choice(["positive", "negative", "none"])
    if correlation_type == "positive":
        y = x * rng.uniform(0.5, 2.0) + rng.normal(0, 5 * difficulty, n_rows)
    elif correlation_type == "negative":
        y = -x * rng.uniform(0.5, 2.0) + 100 + rng.normal(0, 5 * difficulty, n_rows)
    else:
        y = rng.uniform(0, 100, n_rows)

    rows = [
        {"id": i + 1, "x": round(float(x[i]), 2), "y": round(float(y[i]), 2)}
        for i in range(n_rows)
    ]
    return {
        "columns": ["id", "x", "y"],
        "rows": rows,
        "metadata": {
            "task": "Identify the type of correlation between x and y.",
            "options": ["positive", "negative", "none"],
            "correct_correlation_type": correlation_type,
        },
    }


def _generate_clean_dataset(difficulty: int = 1) -> dict:
    n_rows = 20 + difficulty * 5
    rng = np.random.default_rng()

    rows = []
    dirty_indices = random.sample(range(n_rows), difficulty * 2)
    for i in range(n_rows):
        age = int(rng.integers(18, 80))
        salary = round(float(rng.uniform(30000, 120000)), 2)
        if i in dirty_indices:
            age = random.choice([-5, 999, None])
            salary = random.choice([-100, None, float("nan")])
            salary = None if (isinstance(salary, float) and np.isnan(salary)) else salary
        rows.append({"id": i + 1, "age": age, "salary": salary})

    return {
        "columns": ["id", "age", "salary"],
        "rows": rows,
        "metadata": {
            "task": "Identify and mark rows with invalid/dirty data.",
            "dirty_indices": dirty_indices,
        },
    }


def _generate_trend_dataset(difficulty: int = 1) -> dict:
    n_points = 20 + difficulty * 10
    rng = np.random.default_rng()
    trend = random.choice(["increasing", "decreasing", "stable", "cyclic"])

    t = np.arange(n_points)
    if trend == "increasing":
        values = t * rng.uniform(1, 3) + rng.normal(0, 2 * difficulty, n_points)
    elif trend == "decreasing":
        values = -t * rng.uniform(1, 3) + n_points * 3 + rng.normal(0, 2 * difficulty, n_points)
    elif trend == "cyclic":
        values = 20 * np.sin(2 * np.pi * t / 10) + rng.normal(0, difficulty, n_points)
    else:
        values = rng.normal(50, 2 * difficulty, n_points)

    rows = [{"id": i + 1, "time": int(t[i]), "value": round(float(values[i]), 2)} for i in range(n_points)]
    return {
        "columns": ["id", "time", "value"],
        "rows": rows,
        "metadata": {
            "task": "Identify the trend in the time series.",
            "options": ["increasing", "decreasing", "stable", "cyclic"],
            "correct_trend": trend,
        },
    }
