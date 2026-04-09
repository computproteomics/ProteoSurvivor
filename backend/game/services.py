"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""

import random
from typing import Any, cast
import pandas as pd
from .models import StationRun
import pandas
import numpy as np
from .serializers import DataFrameSessionSerializer
from .helper_functions import boxplot, adjusted_pvalue_histograms_by_species
from statsmodels.stats.multitest import multipletests 
from qvalue import qvalue


STATION_SIMULATORS = {}


def _to_json_safe(value: Any) -> Any:
    """Convert values to JSON-safe primitives for DRF responses."""
    if value is None:
        return None

    if value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.floating):
        float_value = float(value)
        return float_value if np.isfinite(float_value) else None

    if isinstance(value, float):
        return value if np.isfinite(value) else None

    return value


def run_station(request, station_id: str, params: dict) -> dict[str, Any]:
    """
    Simulate the execution of a proteomics lab station with the given parameters.
    Returns a dictionary with the simulation results.
    """
    print(f"Running station '{station_id}' with parameters: {params}")
    dataset = request.session.get("current_dataset", None)
    if dataset is not None:
        dataset = DataFrameSessionSerializer.loads(dataset)
    runner = STATION_SIMULATORS.get(station_id)
    if runner is None:
        raise ValueError(f"Unknown station '{station_id}'.")

    result = runner(dataset, params)
    print(f"Simulation result for station '{station_id}': {result}")
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
        print(f"Saved StationRun with ID {run.id} for user {request.user.username}")
    request.session["current_dataset"] = DataFrameSessionSerializer.dumps(result.get("dataset", dataset))
    print(f"Updated session dataset for user {request.user.username}")

    # Keep large internal data structures (e.g., DataFrames) in session only.
    response_payload = {key: value for key, value in result.items() if key != "dataset"}
    return cast(dict[str, Any], _to_json_safe(response_payload))


def _simulate_sample_prep(dataset: dict, params: dict) -> dict:
    return {
        "success": True,
        "feedback": "Sample preparation intro completed.",
        "score": 0,
        "dataset": dataset,
    }


def _simulate_mass_spec(dataset: dict, params: dict) -> dict:
    return {
        "success": True,
        "feedback": "Mass spectrometry intro completed.",
        "score": 0,
        "dataset": dataset,
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

def _simulate_transform(dataset: pd.DataFrame, params: dict) -> dict:
    method = params.get("transform_method", "none")
    if dataset is None:
        df = pd.DataFrame()
    else:
        df = dataset.copy()
    relevant_cols = [col for col in df.columns if col.startswith("LFQ")]
    imgs = []
    success = False
    feedback = None

    try:
        img_before = boxplot(df, relevant_cols, title="Intensities Before Transformation")
        imgs.append(img_before)

        if method == "none":
            success = True
            feedback = "No transformation applied. Data remains unchanged."

        elif method == "log2":
            df[relevant_cols] = np.log2(df[relevant_cols])
            img_after = boxplot(df, relevant_cols, title="Intensities After Transformation (Log2)")
            imgs.append(img_after)
            success = True
            feedback = "Log2 transformation applied. Variance stabilized for downstream analysis."

        elif method == "ln":
            df[relevant_cols] = np.log(df[relevant_cols])
            img_after = boxplot(df, relevant_cols, title="Intensities After Transformation (Natural Log)")
            imgs.append(img_after)
            success = True
            feedback = "Natural log transformation applied. Variance stabilized for downstream analysis."

    except Exception as e:
        success = False
        feedback = f"Error applying transformation: {str(e)}"

    return {
        "success": success,
        "num_pro": None,
        "num_pep": None,
        "feedback": feedback,
        "img": imgs,
        "score": 0,
        "dataset": df
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


def _simulate_multiple_testing_corrector(dataset: pd.DataFrame, params: dict) -> dict:
    method = params.get("correction_method", "none")
    
    success = False
    imgs = []
    score = 0
    
    # Handle missing dataset
    if dataset is None:
        return {
            "success": success,
            "num_prot": None,
            "num_pep": None,
            "feedback": "No dataset available. Cannot perform multiple testing correction.",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame()
        }
    else:
        df = dataset.copy()
    
    p_val_col = "p_value"

    # Handle missing p-value column
    if p_val_col not in df.columns:
        return {
            "success": success,
            "num_prot": int(df["Protein ID"].nunique()),
            "num_pep": int(df["Combined Total Peptides"].sum()),
            "feedback": f"Column '{p_val_col}' not found in dataset. Cannot perform multiple testing correction.",
            "img": imgs,
            "score": score,
            "dataset": df
        }

    pvals = df[p_val_col].values

    try:
        if method == "none":
            df["p_adjusted"] = df["p_value"]  # No adjustment, just copy p-values
            success = True
            feedback = "No multiple testing correction applied. Raw p-values are used for significance assessment."
        elif method == "bh":
            adjusted = multipletests(pvals, method="fdr_bh")
            df["p_adjusted"] = adjusted[1]
            success = True
            feedback = "Benjamini-Hochberg correction applied. Controls the false discovery rate (FDR) under independence assumptions."
        elif method == "bt":
            adjusted = multipletests(pvals, method="fdr_by")
            df["p_adjusted"] = adjusted[1]
            success = True
            feedback = "Benjamini-Tekutieli correction applied. Controls the FDR under arbitrary dependence assumptions."
        elif method == "storey":
            qvals = qvalue(pvals)
            df["p_adjusted"] = qvals
            success = True
            feedback = "Storey's q-value method applied. Estimates the proportion of true null hypotheses to improve power."
        elif method == "bonferroni":
            adjusted = multipletests(pvals, method="bonferroni")
            df["p_adjusted"] = adjusted[1]
            success = True
            feedback = "Bonferroni correction applied. Controls the family-wise error rate (FWER) but can be overly conservative."
        elif method == "holm":
            adjusted = multipletests(pvals, method="holm")
            df["p_adjusted"] = adjusted[1]
            success = True
            feedback = "Holm-Bonferroni correction applied. Controls the family-wise error rate (FWER) with more power than Bonferroni."
    except Exception as e:
        success = False
        feedback = f"Error applying multiple testing correction: {str(e)}"

    if success and "p_adjusted" in df.columns:
        imgs.extend(
            adjusted_pvalue_histograms_by_species(
                df,
                value_col="p_adjusted",
                species_col="Organism",
            )
        )

    return {
        "success": success,
        "num_prot": int(df["Protein ID"].nunique()),
        "num_pep": int(df["Combined Total Peptides"].sum()),
        "feedback": feedback,
        "img": imgs,
        "score": 0,
        "dataset": df
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

    # TODO should return a new col "p_value"

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
