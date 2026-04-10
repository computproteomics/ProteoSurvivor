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
from .helper_functions import boxplot

from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from sklearn.ensemble import RandomForestRegressor

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
    """""
    Simulate imputation of missing values in proteomics data based on selected method.
    - "none"        : No imputation, missing values remain as is.
    - "knn"         : k-nearest neighbors imputation with k = 5.
    - "regression"  : Regression-based imputation.
    - "randomforest": Random forest imputation.
    - "bayesian"    : Bayesian imputation.
    - "minprob"     : Impute with random values drawn from a distribution of low 
                      intensities.
    - "median"      : Impute with the median of each protein across samples.
    - "mean"        : Impute with the mean of each protein across samples.
    """""

    method = str(params.get("imputation_method", "none")).lower()
    if dataset is None:
        df = pd.DataFrame()
    else:
        df = dataset.copy()
    relevant_cols = [c for c in df.columns if c.endswith("MaxLFQ Intensity")]

    imgs: list[str] = []
    success = False
    feedback = None
    
    # Sanity check
    if not relevant_cols:
        return {
            "success": False,
            "num_pro": None,
            "num_pep": None,
            "feedback": "No intensity columns found for imputation.",
            "img": imgs,
            "score": 0,
            "dataset": df,
        }

    # Numberic matrix for imputation work
    x = (
        df[relevant_cols]
        .apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .copy()
    )

    # Function to impute missing values based on method
    def impute_matrix(x: pandas.DataFrame, method: str) -> pandas.DataFrame:

        if method == "none":
            return x
        
        if method == "mean":
            imputer = SimpleImputer(strategy="mean")
        elif method == "median":
            imputer = SimpleImputer(strategy="median")
        elif method == "knn":
            imputer = KNNImputer(n_neighbors=5)
        elif method == "regression":
            imputer = IterativeImputer(
                estimator = LinearRegression(),
                random_state = 42,
                max_iter = 15
            )
        elif method == "randomforest":
            imputer = IterativeImputer(
                estimator=RandomForestRegressor(
                    n_estimators=200,
                    random_state=42,
                    n_jobs=-1
                ),
                random_state=42,
                max_iter=10
            )
        elif method == "bayesian":
            imputer = IterativeImputer(
                estimator = BayesianRidge(),
                sample_posterior = True,
                random_state = 42,
                max_iter = 15
            )
        elif method == "minprob":
            out = x.copy()
            rng = np.random.default_rng(42)
            for col in out.columns:
                miss = out[col].isna()
                if not miss.any():
                    continue
                obs = out[col].dropna()
                if obs.empty:
                    continue
                mu = float(obs.mean())
                sigma = float(obs.std())
                out.loc[miss, col] = rng.normal(mu - 1.8 * sigma, 0.3 * sigma, size=miss.sum())
            return out
        else:
            raise ValueError(f"Unknown imputation method: {method}")

        arr = imputer.fit_transform(x)
        return pandas.DataFrame(arr, index=x.index, columns=x.columns)

    feedback_by_method = {
        "none": "No imputation applied. Missing values remain as is.",
        "mean": "Mean imputation applied across samples.",
        "median": "Median imputation applied across samples.",
        "knn": "kNN imputation applied with k = 5.",
        "regression": "Regression-based imputation applied.",
        "randomforest": "Random forest-based iterative imputation applied.",
        "bayesian": "Bayesian ridge-based iterative imputation applied.",
        "minprob": "MinProb imputation applied using low-intensity random draws.",
    }

    try:
        x_new = impute_matrix(x, method)
        df_new = df.copy()
        df_new[relevant_cols] = x_new
        success = True
        feedback = feedback_by_method.get(method, f"Imputation method '{method}' applied.")
    except Exception as e:
        df_new = df.copy()
        success = False
        feedback = f"Error applying imputation: {str(e)}"


    return {
        "success": success,
        "num_pro": None,
        "num_pep": None,
        "feedback": feedback,
        "img": imgs,
        "score": 0,
        "dataset": df_new
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
