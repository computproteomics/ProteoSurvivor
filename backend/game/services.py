"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""

import random
from .models import StationRun
import pandas


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
        score=result.get(
            "score", 0
        ),  # Score can be calculated based on results if needed
    )
    if result.get("success"):
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
        "score": round(
            protein_yield * (100 - missed) / 100, 2
        ),  # example scoring formula
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


def _simulate_spectral_search(dataset: dict, params: dict) -> dict:

    tool = params.get("tool", "fragpipe")
    match_between_runs = params.get("match_between_runs", "FALSE")
    # set match_between_runs to upper case
    match_between_runs = match_between_runs.upper()
    precursor_mass_tolerance = int(params.get("precursor_mass_tolerance", 5))
    fragment_mass_tolerance = params.get("fragment_mass_tolerance", "0.01")
    enzyme = params.get("enzyme", "stricttrypsin")
    missed_cleavages = int(params.get("missed_cleavages", 1))
    min_pep_len = int(params.get("min_peptide_length", 7))
    max_pep_len = int(params.get("max_peptide_length", 35))

    file_map = pandas.read_csv("data/ParameterTable.csv")  # Mapping table
    # Make key of all columns but ParameterSet
    file_map["key"] = (
        file_map["tool"]
        + "_mbf"
        + file_map["match_between_runs"].astype(str).str.upper()
        + "_pmt"
        + file_map["precursor_mass_tolerance"].astype(str)
        + "_ft"
        + file_map["fragment_mass_tolerance"].astype(str)
        + "_enzyme"
        + file_map["enzyme"].astype(str)
        + "_mc"
        + file_map["missed_cleavages"].astype(str)
        + "_minpl"
        + file_map["min_peptide_length"].astype(str)
        + "_maxpl"
        + file_map["max_peptide_length"].astype(str)
    )
    # get the data file name for the current parameters
    file_key = (
        tool
        + "_mbf"
        + str(match_between_runs).upper()
        + "_pmt"
        + str(precursor_mass_tolerance)
        + "_ft"
        + str(fragment_mass_tolerance)
        + "_enzyme"
        + str(enzyme)
        + "_mc"
        + str(missed_cleavages)
        + "_minpl"
        + str(min_pep_len)
        + "_maxpl"
        + str(max_pep_len)
    )

    # if multiples rows match, take the first one (shouldn't happen if ParameterTable.csv is well-constructed)

    print(f"Looking for data file with key: {file_key}")
    print(f"Available keys in file map: " + file_map["key"][0])
    matching_rows = file_map[file_map["key"] == file_key]
    if matching_rows.empty:
        raise ValueError(f"No data file found for parameters: {params}")
    data_file_name = matching_rows.iloc[0]["ParameterSet"] + ".tsv"

    # Load the corresponding data file and extract results
    dataset = pandas.read_csv(f"data/{data_file_name}", sep="\t")

    return {
        "success": True,
        "dataset": dataset,
        "num_prot": int(dataset["Protein ID"].nunique()),
        "num_pep": int(dataset["Combined Total Peptides"].sum()),
        "img": [],
        "score": 0,
        "feedback": """
        Done: You now ran a peptide database search with FragPipe using the given search parameters. 
        The software takes the mass spectra from the mass spectrometer and compares them to theoretical spectra generated from a protein sequence database.
        The result is a list of identified peptides and proteins, along with scores indicating the confidence of each identification.
        From now on, you will use the protein table for the next stations. It contains the identified proteins and their associated data, such as the number of peptides identified for each protein, 
        protein length, identification confidence, and quantification values (among more information)
        You can now proceed to the next station to further process and analyze these identifications.
        """,
    }


def _simulate_transform(dataset: dict, params: dict) -> dict:
    method = params.get("transform_method", "none")

    variance = random.uniform(0.5, 1.5)

    if method in ["ln", "log2"]:
        variance *= 0.6

    return {
        "summary": f"Applied {method} transformation.",
        "variance": round(variance, 3),
        "effect": "Variance stabilized." if method != "none" else "No change.",
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
        "removed_fraction": round(reduction, 2),
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
        "status": "Normalized" if method != "none" else "Skipped",
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
        "recovered_fraction": round(recovered, 2),
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
        "adjusted_significant": adjusted,
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
        "cutoffs": {"log2FC": fc, "FDR": pval},
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
        "significant_features": int(power * random.randint(100, 500)),
    }


STATION_SIMULATORS.update(
    {
        "sample_prep": _simulate_sample_prep,
        "mass_spec": _simulate_mass_spec,
        "spectral_search": _simulate_spectral_search,
        "filtering": _simulate_filtering,
        "transform": _simulate_transform,
        "normalize": _simulate_normalize,
        "imputer": _simulate_normalize,
        "multiple_testing_corrector": _simulate_multiple_testing_corrector,
        "the_cutter": _simulate_the_cutter,
        "statistical_analysis": _simulate_statistical_analysis,
        # ...
    }
)
"""Additional station simulators can be added to the STATION_SIMULATORS dict following the same pattern.
The key MUST correspond to the station_id used in the frontend configuration (frontend/src/assets/stations.json),
and the value is a function that takes (dataset, params) and returns a dict with results."""
