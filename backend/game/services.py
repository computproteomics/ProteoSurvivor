"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""
import random
from .models import StationRun


STATION_SIMULATORS = {}


def run_station(request, station_id: str, params: dict) -> StationRun:
    """
    Simulate the execution of a proteomics lab station with the given parameters.
    Returns a persisted StationRun with results populated.
    """

    dataset = request.session.get("current_dataset", None)
    runner = STATION_SIMULATORS.get(station_id)
    if runner is None:
        raise ValueError(f"Unknown station '{station_id}'.")

    result = runner(dataset, params)

    run = StationRun(
        player=request.user,
        station_id=station_id,
        params=params,
        score=result.get("score", 0),  # Score can be calculated based on results if needed
    )
    run.save()
    request.session["current_dataset"] = result.get("dataset", dataset)
    return result


def _simulate_sample_prep(dataset: dict, params: dict) -> dict:
    enzyme = params.get("enzyme", "trypsin")
    lysis = params.get("lysis_method", "chemical")
    reduction = params.get("reduction_agent", "DTT")
    alkylation = params.get("alkylation_agent", "iodoacetamide")

    protein_yield = round(random.uniform(1.2, 4.8), 2)
    peptide_count = random.randint(8000, 22000)
    missed = random.randint(5, 18)

    quality = "High" if enzyme == "trypsin" and lysis == "chemical" else "Medium"

    return {
        "dataset": dataset,  # updated dataset
        "score": round(protein_yield * (100 - missed) / 100, 2),  # example scoring formula
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


def _simulate_mass_spec(dataset: dict, params: dict) -> dict:
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


STATION_SIMULATORS.update({
        "sample_prep": _simulate_sample_prep,
        "mass_spec": _simulate_mass_spec,
        # ...
    })
"""Additional station simulators can be added to the STATION_SIMULATORS dict following the same pattern.
The key MUST correspond to the station_id used in the frontend configuration (frontend/src/assets/stations.json),
and the value is a function that takes (dataset, params) and returns a dict with results."""