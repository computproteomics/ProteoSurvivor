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
    return {
        "success": True,
        "feedback": "Sample preparation intro completed.",
        "score": None,
        "dataset": dataset,
    }


def _simulate_mass_spec(dataset: dict, params: dict) -> dict:
    return {
        "success": True,
        "feedback": "Mass spectrometry intro completed.",
        "score": None,
        "dataset": dataset,
    }

def _simulate_spectral_search(dataset: dict, params: dict) -> dict:
    tool = params.get("tool", "fraqpipe")
    tol = int(params.get("precursor_mass_tolerance", 10))
    enzyme = params.get("enzyme", "trypsin")

    proteins = 100

    return {
        "summary": f"{tool} search complete with {tol} ppm tolerance using {enzyme}.",
        "proteins": proteins,
    }

def _simulate_transform(dataset: dict, params: dict) -> dict:
    method = params.get("transform_method", "none")

    variance = random.uniform(0.5, 1.5)

    if method in ["ln", "log2"]:
        variance *= 0.6

    return {
        "summary": f"Applied {method} transformation.",
        "variance": round(variance, 3),
        "effect": "Variance stabilized." if method != "none" else "No change."
    }

def _simulate_filtering(dataset: dict, params: dict) -> dict:
    remove_cont = params.get("remove_contaminants", "yes") == "yes"
    missing_thresh = int(params.get("remove_missing_proteins", 0))

    proteins = dataset.get("proteins", 1000)

    reduction = 0.1 if remove_cont else 0
    reduction += missing_thresh * 0.02

    filtered = int(proteins * (1 - reduction))

    return {
        "summary": "Filtering complete.",
        "proteins_before": proteins,
        "proteins_after": filtered,
        "removed_fraction": round(reduction, 2)
    }

def _simulate_normalize(dataset: dict, params: dict) -> dict:
    method = params.get("normalization", "none")

    if method == "none":
        shift = 0
    elif method in ["median", "total_intensity"]:
        shift *= 0.5
    elif method in ["quantile", "vsn"]:
        shift *= 0.3

    return {
        "summary": f"{method} normalization applied.",
        "batch_effect": round(shift, 3),
        "status": "Normalized" if method != "none" else "Skipped"
    }

def _simulate_imputer(dataset: dict, params: dict) -> dict:
    method = params.get("imputation_method", "none")

    missing = random.uniform(0.05, 0.3)

    if method == "none":
        recovered = 0
    else:
        recovered = missing * random.uniform(0.6, 0.95)

    return {
        "summary": f"{method} imputation applied.",
        "missing_fraction": round(missing, 2),
        "recovered_fraction": round(recovered, 2)
    }

def _simulate_multiple_testing_corrector(dataset: dict, params: dict) -> dict:
    method = params.get("correction_method", "none")

    raw_hits = random.randint(200, 800)

    if method == "bonferroni":
        adjusted = int(raw_hits * 0.3)
    elif method in ["bh", "holm"]:
        adjusted = int(raw_hits * 0.6)
    elif method == "storey":
        adjusted = int(raw_hits * 0.7)
    else:
        adjusted = raw_hits

    return {
        "summary": f"{method} correction applied.",
        "raw_significant": raw_hits,
        "adjusted_significant": adjusted
    }

def _simulate_the_cutter(dataset: dict, params: dict) -> dict:
    fc = float(params.get("fold_change_cutoff", 1))
    pval = float(params.get("pvalue_cutoff", 0.05))

    candidates = random.randint(50, 300)

    strictness = fc * (1 / pval)
    final_hits = int(candidates / (1 + strictness * 0.1))

    return {
        "summary": "Final candidate selection complete.",
        "initial_candidates": candidates,
        "final_hits": final_hits,
        "cutoffs": {"log2FC": fc, "FDR": pval}
    }

def _simulate_statistical_analysis(dataset: dict, params: dict) -> dict:
    test = params.get("statistical_test", "none")

    power = random.uniform(0.5, 0.9)

    if test in ["limma", "anova"]:
        power += 0.1
    elif test == "none":
        power = 0

    return {
        "summary": f"{test} analysis completed.",
        "statistical_power": round(power, 2),
        "significant_features": int(power * random.randint(100, 500))
    }

STATION_SIMULATORS.update({
        "sample_prep": _simulate_sample_prep,
        "mass_spec": _simulate_mass_spec,
        "filtering": _simulate_filtering,
        "spectral_search": _simulate_spectral_search,
        "transform": _simulate_transform,
        "normalize": _simulate_normalize,
        "imputer": _simulate_normalize,
        "multiple_testing_corrector": _simulate_multiple_testing_corrector,
        "the_cutter": _simulate_the_cutter,
        "statistical_analysis": _simulate_statistical_analysis,
        # ...
    })
"""Additional station simulators can be added to the STATION_SIMULATORS dict following the same pattern.
The key MUST correspond to the station_id used in the frontend configuration (frontend/src/assets/stations.json),
and the value is a function that takes (dataset, params) and returns a dict with results."""