"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""
import random
from django.utils import timezone
from .models import GameSession, Score, StationRun


def run_station(station_id: str, params: dict, player=None) -> StationRun:
    """
    Simulate the execution of a proteomics lab station with the given parameters.
    Returns a persisted StationRun with results populated.
    """
    simulators = {
        "sample_prep": _simulate_sample_prep,
        "mass_spec": _simulate_mass_spec,
        "spectral_search": _simulate_spectral_search,
        "filtering": _simulate_filtering,
        "transform": _simulate_transform,
        "normalize": _simulate_normalize,
        "imputer": _simulate_imputer,
        "multiple_testing_corrector": _simulate_multiple_testing_corrector,
        "the_cutter": _simulate_the_cutter,
        "statistical_analysis": _simulate_statistical_analysis,
        "veit": _simulate_veit,
    }
    simulate = simulators.get(station_id, _simulate_default)
    results = simulate(params)

    run = StationRun.objects.create(
        player=player,
        station_id=station_id,
        params=params,
        results=results,
        status="completed",
    )
    return run


def _simulate_sample_prep(params: dict) -> dict:
    enzyme = params.get("enzyme", "trypsin")
    lysis = params.get("lysis_method", "chemical")
    reduction = params.get("reduction_agent", "DTT")
    alkylation = params.get("alkylation_agent", "iodoacetamide")

    protein_yield = round(random.uniform(1.2, 4.8), 2)
    peptide_count = random.randint(8000, 22000)
    missed = random.randint(5, 18)

    quality = "High" if enzyme == "trypsin" and lysis == "chemical" else "Medium"

    return {
        "summary": (
            f"Sample preparation completed using {lysis} lysis, "
            f"{reduction} reduction, and {alkylation} alkylation."
        ),
        "protein_yield_mg_ml": protein_yield,
        "estimated_peptides": peptide_count,
        "missed_cleavage_rate_pct": missed,
        "enzyme_used": enzyme,
        "sample_quality": quality,
        "recommendation": (
            "Proceed to mass spectrometry."
            if quality == "High"
            else "Consider repeating lysis with chemical method for higher yield."
        ),
    }


def _simulate_mass_spec(params: dict) -> dict:
    mode = params.get("acquisition_mode", "DDA")
    gradient = int(params.get("gradient_length_min", 60))
    ms1_res = int(params.get("ms1_resolution", 60000))

    psm_base = 18000 if mode == "DIA" else 12000
    psm_count = random.randint(int(psm_base * 0.85), int(psm_base * 1.15))
    peptides = random.randint(int(psm_count * 0.6), int(psm_count * 0.8))
    proteins = random.randint(int(peptides * 0.08), int(peptides * 0.12))
    coverage = round(random.uniform(55, 82), 1)

    return {
        "summary": (
            f"Acquisition finished: {mode} mode, {gradient} min gradient, "
            f"MS1 resolution {ms1_res:,}."
        ),
        "psm_count": psm_count,
        "peptide_count": peptides,
        "protein_groups": proteins,
        "sequence_coverage_pct": coverage,
        "acquisition_mode": mode,
        "recommendation": (
            "Good coverage. Proceed to database search."
            if coverage >= 65
            else "Coverage is low — consider a longer gradient next time."
        ),
    }


def _simulate_spectral_search(params: dict) -> dict:
    db = params.get("database", "SwissProt")
    enzyme = params.get("enzyme", "trypsin")
    missed = int(params.get("missed_cleavages", 2))
    fdr = float(params.get("fdr_threshold", 0.01))

    db_sizes = {"SwissProt": 20430, "TrEMBL": 248947, "RefSeq": 114532}
    db_size = db_sizes.get(db, 20430)

    protein_groups = random.randint(3800, 5200)
    peptides = random.randint(protein_groups * 8, protein_groups * 14)
    decoy_fdr = round(random.uniform(fdr * 0.3, fdr * 0.9), 4)

    return {
        "summary": (
            f"Spectral search completed against {db} ({db_size:,} entries) "
            f"with {enzyme}, up to {missed} missed cleavages at {fdr*100:.0f}% FDR."
        ),
        "protein_groups_identified": protein_groups,
        "peptides_identified": peptides,
        "database_used": db,
        "actual_fdr": decoy_fdr,
        "fdr_threshold": fdr,
        "recommendation": (
            "Identifications look solid. Proceed to data analysis."
            if protein_groups >= 4000
            else "Fewer identifications than expected — consider a larger database."
        ),
    }


def _simulate_filtering(params: dict) -> dict:
    confidence = int(params.get("min_confidence_score", 70))
    contaminants = params.get("remove_contaminants", "yes")

    retained = random.randint(3500, 5200)
    removed = random.randint(120, 650)

    return {
        "summary": (
            f"Filtering completed with minimum confidence {confidence} and "
            f"contaminant removal set to {contaminants}."
        ),
        "entries_retained": retained,
        "entries_removed": removed,
        "recommendation": "Proceed to data transform.",
    }


def _simulate_transform(params: dict) -> dict:
    method = params.get("transform_method", "log2")
    return {
        "summary": f"Data transformation completed using {method}.",
        "skewness_before": round(random.uniform(1.4, 2.9), 2),
        "skewness_after": round(random.uniform(0.2, 0.8), 2),
        "recommendation": "Proceed to normalization.",
    }


def _simulate_normalize(params: dict) -> dict:
    method = params.get("normalization", "median")
    return {
        "summary": f"Normalization completed with {method} method.",
        "cv_before_pct": round(random.uniform(18, 31), 1),
        "cv_after_pct": round(random.uniform(8, 15), 1),
        "recommendation": "Proceed to imputation.",
    }


def _simulate_imputer(params: dict) -> dict:
    method = params.get("imputation_method", "knn")
    missing_before = random.randint(900, 2600)
    missing_after = random.randint(0, 40)
    return {
        "summary": f"Missing values imputed using {method}.",
        "missing_values_before": missing_before,
        "missing_values_after": missing_after,
        "recommendation": "Proceed to statistical analysis.",
    }


def _simulate_multiple_testing_corrector(params: dict) -> dict:
    method = params.get("correction_method", "Benjamini-Hochberg")
    alpha = float(params.get("alpha", 0.05))
    significant = random.randint(120, 520)
    return {
        "summary": (
            f"Multiple-testing correction completed using {method} at alpha={alpha:.2f}."
        ),
        "significant_features": significant,
        "recommendation": "Proceed to The Cutter.",
    }


def _simulate_the_cutter(params: dict) -> dict:
    fc = float(params.get("fold_change_threshold", 2.0))
    top_n = int(params.get("keep_top_n", 100))
    kept = min(top_n, random.randint(30, 220))
    return {
        "summary": f"The Cutter applied fold-change threshold {fc}x.",
        "candidates_kept": kept,
        "recommendation": "Proceed to Statistical Analysis.",
    }


def _simulate_statistical_analysis(params: dict) -> dict:
    normalization = params.get("normalization", "median")
    test = params.get("statistical_test", "t-test")
    fdr = float(params.get("fdr_threshold", 0.05))
    fc_threshold = float(params.get("fold_change_threshold", 1.5))

    total_proteins = random.randint(3800, 5200)
    regulated = random.randint(120, 480)
    up = random.randint(int(regulated * 0.4), int(regulated * 0.6))
    down = regulated - up
    top_proteins = ["IFITM3", "MX1", "OAS1", "ISG15", "IFIT1"]

    return {
        "summary": (
            f"Differential expression analysis using {normalization} normalisation, "
            f"{test} at {fdr*100:.0f}% FDR, fold-change threshold {fc_threshold}×."
        ),
        "total_proteins_quantified": total_proteins,
        "significantly_regulated": regulated,
        "up_regulated": up,
        "down_regulated": down,
        "top_hits": top_proteins,
        "normalization_used": normalization,
        "statistical_test": test,
        "recommendation": (
            "Clear antiviral response signature detected. "
            "Report findings to Veit."
        ),
    }


def _simulate_veit(params: dict) -> dict:
    report = params.get("report_text", "").strip()
    keywords = ["regulated", "pathway", "protein", "antiviral", "interferon", "analysis"]
    hits = sum(1 for kw in keywords if kw.lower() in report.lower())
    quality = "Excellent" if hits >= 4 else ("Good" if hits >= 2 else "Needs improvement")

    if quality == "Excellent":
        feedback = "Great work! Your report covers the key findings of the proteomics experiment."
    elif quality == "Good":
        feedback = "Good effort. Try to mention specific pathways and regulated proteins."
    else:
        feedback = "Your report is missing key details. Describe which proteins were regulated and why."

    recommendation = (
        "Experiment complete — return to the world map."
        if quality != "Needs improvement"
        else "Revise your report and try again."
    )

    return {
        "summary": "Veit has reviewed your report.",
        "report_quality": quality,
        "keywords_found": hits,
        "feedback": feedback,
        "recommendation": recommendation,
    }


def _simulate_default(params: dict) -> dict:
    return {"summary": "Station completed.", "params_received": params}





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
