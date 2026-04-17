"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""

import random
from typing import Any, cast
import pandas as pd
from .models import StationRun, FinalStationResult
import numpy as np
import os
from .serializers import DataFrameSessionSerializer
from .helper_functions import (
    tr_boxplot,
    sp_scatterplot,
    mtc_histograms,
    _create_histogram,
    imputer_before_after_stripgrid,
    histogram_compare,
    plot_significant_proteins,
    plot_scores,
    volcano_plot,
    filtering_scatterplot,
    filtering_piechart,
)
from statsmodels.stats.multitest import multipletests
from py_qvalue import qvalue as _py_qvalue

from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from sklearn.ensemble import RandomForestRegressor

from scipy.stats import ttest_ind, mannwhitneyu, permutation_test

from django.conf import settings

# Variables for column names
PROTEIN = "Protein"
PROTEIN_ID = "Protein ID"
ENTRY = "Entry Name"
GENE = "Gene"
PROTEIN_LENGTH = "Protein Length"
ORGANISM = "Organism"
EXISTENCE = "Protein Existence"
DESCRIPTION = "Description"
PROBABILITY = "Protein Probability"
TOP_PEP_PROB = "Top Peptide Probability"
TOT_PEP = "Total Peptides"
SPEC_COUNT = "Spectral Count"
UNIQUE_SPEC_COUNT = "Unique Spectral Count"
TOT_SPEC_COUNT = "Total Spectral Count"
# NO_USE_INTENSITY_COND_A_REP_01 = "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_01 Intensity"
# NO_USE_INTENSITY_COND_A_REP_02 = "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_02 Intensity"
# NO_USE_INTENSITY_COND_A_REP_03 = "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_03 Intensity"
# NO_USE_INTENSITY_COND_B_REP_01 = "LFQ_Orbitrap_DDA_Condition_B_Sample_Beta_01 Intensity"
# NO_USE_INTENSITY_COND_B_REP_02 = "LFQ_Orbitrap_DDA_Condition_B_Sample_Beta_02 Intensity"
# NO_USE_INTENSITY_COND_B_REP_03 = "LFQ_Orbitrap_DDA_Condition_B_Sample_Beta_03 Intensity"
N_REP = 3
COND_A = [f"ConditionA_Sample{i:02d}" for i in range(1, N_REP + 1)]
COND_B = [f"ConditionB_Sample{i:02d}" for i in range(1, N_REP + 1)]
INDIS_PROTEINS = "Indistinguishable Proteins"

PVALUE = "p_value"
FC = "fold_change"
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

    visited_station_list = request.session.get("visited_stations", [])
    if request.user.is_authenticated:
        user_runs = request.user.station_runs.all()
        visited_stations = set(run.station_id for run in user_runs)
    else:
        visited_stations = set(visited_station_list)

    result = runner(dataset, params, visited_stations)

    print(f"Simulation result for station '{station_id}': {result}")
    if result.get("success"):
        if request.user.is_authenticated:
            run = StationRun(
                player=request.user,
                station_id=station_id,
                params=params,
                score=result.get(
                    "score", 0
                ),  # Score can be calculated based on results if needed
            )

            run.save()
            print(f"Saved StationRun with ID {run.id} for user {request.user.username}")
            if settings.STATIONS_CONFIG[station_id].get("final", False):
                final_result = FinalStationResult(
                    station_run=run,
                    true_positives=result.get("true_positives", 0),
                    false_positives=result.get("false_positives", 0),
                )
                final_result.save()
                print(f"Saved FinalStationResult for StationRun ID {run.id}")
        else:
            if station_id not in visited_station_list:
                visited_station_list.append(station_id)
            request.session["visited_stations"] = visited_station_list

    request.session["current_dataset"] = DataFrameSessionSerializer.dumps(
        result.get("dataset", dataset)
    )
    if request.user.is_authenticated:
        print(f"Updated session dataset for user {request.user.username}")
    else:
        print("Updated session dataset for anonymous user")

    # Keep large internal data structures (e.g., DataFrames) in session only.
    response_payload = {key: value for key, value in result.items() if key != "dataset"}
    return cast(dict[str, Any], _to_json_safe(response_payload))


def _simulate_sample_prep(dataset: dict, params: dict, visited_stations: set) -> dict:
    return {
        "success": True,
        "feedback": "✅ Sample preparation complete. Strangely, your peptides made it through intact despite improbable handling, questionable luck, and the general hostility of the universe.",
        "score": 0,
        "dataset": dataset,
    }


def _simulate_mass_spec(dataset: dict, params: dict, visited_stations: set) -> dict:

    if "sample_prep" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Nice try. The mass spec refuses to run on unprepared samples and pure optimism. Do sample prep first.",
            "score": 0,
            "dataset": dataset,
        }
    return {
        "success": True,
        "feedback": "✅ Mass spectrometry complete. Somehow the peptides survived the ionization gauntlet and emerged as usable spectra.",
        "score": 0,
        "dataset": dataset,
    }


def _simulate_spectral_search(
    dataset: dict, params: dict, visited_stations: set
) -> dict:

    if "sample_prep" and "mass_spec" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Spectral search is locked. The mass spectrometer must run first, or you are searching for peptides in pure imagination.",
            "score": 0,
            "dataset": dataset,
        }

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

    # reading parameter file
    file_map = pd.read_csv("data/ParameterTable.csv")  # Mapping table
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
    matching_rows = file_map[file_map["key"] == file_key]
    if matching_rows.empty:
        raise ValueError(f"No data file found for parameters: {params}")
    data_file_name = matching_rows.iloc[0]["ParameterSet"] + ".tsv"

    # check whether datafile exists
    if not os.path.exists(f"data/{data_file_name}"):
        return {
            "success": False,
            "feedback": "⚠️ No search result exists for this parameter combo. You have discovered a forbidden FragPipe timeline.",
            "score": 0,
            "dataset": dataset,
        }

    # Load the corresponding data file and extract results
    dataset = pd.read_csv(f"data/{data_file_name}", sep="\t")

    # Making plots
    imgs = []
    success = False
    feedback = None

    species_palette = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    # Name the species palette based on the unique species in the dataset
    unique_species = dataset["Organism"].unique()
    species_palette = {
        species: species_palette[i % len(species_palette)]
        for i, species in enumerate(unique_species)
    }

    try:
        for species in unique_species:
            species_df = dataset[dataset["Organism"] == species]

            tr_hist = _create_histogram(
                species_df[SPEC_COUNT],
                species + ": spectral counts",
                "Spectral Counts",
                "Frequency",
                30,
                color=species_palette[species],
                xlim=None,
            )
            imgs.append(tr_hist)
            tr_hist = _create_histogram(
                species_df[PROTEIN_LENGTH],
                species + ": protein lengths",
                "Protein Lengths",
                "Frequency",
                30,
                color=species_palette[species],
                xlim=None,
            )
            imgs.append(tr_hist)
            tr_hist = _create_histogram(
                species_df[PROBABILITY],
                species + ": protein identification probabilities",
                "Protein probabilities",
                "Frequency",
                30,
                color=species_palette[species],
                xlim=(0, 1),
            )
            imgs.append(tr_hist)

        success = True
        feedback = None

    except Exception as e:
        success = False
        feedback = f"Error plotting spectra counts: {str(e)}"

    return {
        "success": success,
        "dataset": dataset,
        "num_prot": int(dataset[PROTEIN].nunique()),
        "num_pep": int(dataset[TOT_PEP].sum()),
        "img": imgs,
        "score": 0,
        "feedback": """
        ✅ Your wizardry has now ran a peptide database search with FragPipe using the given search parameters </br></br>
        FragPipe is a software tool that</br></br>
        1) takes the mass spectra from the mass spectrometer and <i>compares</i> them to theoretical
        spectra generated from a protein sequence database.</br>
        2) creates a list of <i>identified</i> peptides and proteins, along with scores indicating
        the confidence of each identification.</br>
        3) quantifies the identified peptides and proteins based on the intensity of the matched spectra.</br></br>
        From now on, you will use the protein table in the next stations. Fully up to you to screw it up when lives
         are at stake. The search results contain many details about identification such as the identified
         proteins and their associated data, such as the number of peptides identified for each protein,
        protein length, identification confidence, and quantification values. The figures show some of these.</br></br>
        ❗Take a moment to explore the data and the figures. </br/>
        Do you see differences for the different species? </br/>
        Do the values look reasonable?</br/>
        Do you see any differences between species?
        """,
    }


def _simulate_transform(
    dataset: pd.DataFrame, params: dict, visited_stations: set
) -> dict:

    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Transform station is offline until spectral search has produced actual data. Right now you are trying to normalize a rumor.",
            "score": 0,
            "dataset": dataset,
        }

    method = params.get("transform_method", "ln")
    success = False
    imgs = []
    score = 0

    # Handle missing dataset
    if dataset is None or dataset.empty:
        return {
            "success": success,
            "num_pro": None,
            "num_pep": None,
            "feedback": "⚠️ No dataset detected. The transform engine spun bravely but found only void.",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame(),
        }

    df = dataset.copy()
    num_pro = int(df[PROTEIN].nunique()) if PROTEIN in df.columns else 0
    num_pep = int(df[TOT_PEP].sum()) if TOT_PEP in df.columns else 0

    # Updated selector to match current TSV column names
    relevant_cols = COND_A + COND_B

    # check of existing columns
    if not any(col in df.columns for col in relevant_cols):
        # check for more than 2 rows
        if len(df) <= 2:
            return {
                "success": False,
                "num_pro": num_pro,
                "num_pep": num_pep,
                "feedback": "⚠️ Not enough usable intensity data. Even chaos needs numbers before we can tame it.",
                "img": imgs,
                "score": 0,
                "dataset": df,
            }

    try:
        img_before = tr_boxplot(
            df, relevant_cols, title="Intensities Before Transformation"
        )
        imgs.append(img_before)

        if method == "log2":
            df[relevant_cols] = np.log2(df[relevant_cols])
            img_after = tr_boxplot(
                df, relevant_cols, title="Intensities After Transformation (Log2)"
            )
            imgs.append(img_after)
            success = True
            feedback = "✅ Log2 transformation applied. Against all odds, the intensity chaos has been compressed into something statistically survivable."
            score = 10

        elif method == "ln":
            df[relevant_cols] = np.log(df[relevant_cols])
            img_after = tr_boxplot(
                df,
                relevant_cols,
                title="Intensities After Transformation (Natural Log)",
            )
            imgs.append(img_after)
            success = True
            feedback = "✅ Natural log transformation applied. The data is now less explosive and slightly more civilized."
            score = 10

        else:
            success = False
            feedback = f"⚠️ Unknown transformation method {method}. The station refuses experimental wizardry without a known spell."

    except Exception as e:
        success = False
        feedback = f"⚠️ Transformation failed mid-flight: {str(e)}. The proteome remains unconvinced."

    return {
        "success": success,
        "num_pro": num_pro,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": score,
        "dataset": df,
    }


def _simulate_filtering(
    dataset: pd.DataFrame, params: dict, visited_stations: set
) -> dict:

    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Filtering station is locked until spectral search has produced real protein data. Right now you are filtering pure optimism.",
            "score": 0,
            "dataset": dataset,
        }

    missing_thresh = int(params.get("remove_missing_proteins", 0))
    min_pep_num = int(params.get("min_peptides_per_protein", 1))
    success = False
    imgs = []
    score = 0
    df = dataset.copy() if dataset is not None else pd.DataFrame()

    # Handle missing dataset
    if dataset is None or dataset.empty:
        return {
            "success": success,
            "num_pro": None,
            "num_pep": None,
            "feedback": "⚠️ No dataset detected. You reached for proteins and grabbed only the void.",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame(),
        }

    num_pro_before = int(dataset[PROTEIN_ID].nunique())
    num_pep = int(dataset[TOT_PEP].sum())

    # Find intensity columns
    relevant_cols = COND_A + COND_B

    if not relevant_cols:
        return {
            "success": False,
            "num_pro": num_pro_before,
            "num_pep": num_pep,
            "feedback": "⚠️ No usable intensity columns found. The filter has nothing measurable to judge.",
            "img": imgs,
            "score": 0,
            "dataset": df,
        }

    try:

        # Calculate missing values for each protein
        sample_values = df[relevant_cols].replace([np.inf, -np.inf], np.nan)
        missing_num = sample_values.isna().sum(axis=1)

        # Filter proteins: keep only those with missing number <= threshold
        df_filtered = df[missing_num <= missing_thresh].copy()

        # filter for mimimum number of peptides
        df_filtered = df_filtered[df_filtered[TOT_PEP] >= min_pep_num]

        num_pro_after = int(df_filtered[PROTEIN_ID].nunique())
        removed_count = num_pro_before - num_pro_after

        success = True

        feedback = f"✅ Filtering complete. Removed {removed_count} proteins. Against all odds, the survivors now look statistically less cursed."

        # Generate visualizations
        pie_img = filtering_piechart(num_pro_before, num_pro_after)
        if pie_img:
            imgs.append(pie_img)

        scatter_img = filtering_scatterplot(df_filtered, relevant_cols)
        if scatter_img:
            imgs.append(scatter_img)

    except Exception as e:
        success = False
        df_filtered = df
        num_pro_after = num_pro_before
        feedback = f"⚠️ Filtering failed mid-procedure: {str(e)}. The dataset escaped containment."

    return {
        "success": success,
        "num_pro": num_pro_after,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": 0,
        "dataset": df_filtered,
    }


def _simulate_normalize(
    dataset: pd.DataFrame, params: dict, visited_stations: set
) -> dict:

    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Normalization is unavailable until spectral search has produced data worth rescuing. At the moment you are standardizing empty ambition.",
            "score": 0,
            "dataset": dataset,
        }

    method = params.get("normalization", "none")

    if dataset is None:
        df = pd.DataFrame()
    else:
        df = dataset.copy()

    num_pro = int(df[PROTEIN].nunique()) if PROTEIN in df.columns else 0
    num_pep = int(df[TOT_PEP].sum()) if TOT_PEP in df.columns else 0

    relevant_cols = COND_A + COND_B
    imgs = []
    success = False
    feedback = None

    if df.empty:
        return {
            "success": False,
            "num_pro": num_pro,
            "num_pep": num_pep,
            "feedback": "⚠️ Dataset is empty. The normalization engine looked into the abyss and received no intensities in return.",
            "img": imgs,
            "score": 0,
            "dataset": df,
        }

    if not relevant_cols:
        return {
            "success": False,
            "num_pro": num_pro,
            "num_pep": num_pep,
            "feedback": "⚠️ No usable intensity columns found. Normalization requires numbers, not interpretive protein lore.",
            "img": imgs,
            "score": 0,
            "dataset": df,
        }

    df_before = df.copy()

    try:
        if method == "none":
            success = True
            feedback = "✅ No normalization applied. Against convention, the raw values remain untouched."

        elif method == "median":
            df[relevant_cols] = df[relevant_cols].subtract(df[relevant_cols].median())
            success = True
            feedback = "✅ Median normalization applied. The samples have been dragged toward a shared middle ground."

        elif method == "total_intensity":
            col_sums = df[relevant_cols].sum().replace(0, np.nan)
            df[relevant_cols] = df[relevant_cols].divide(col_sums, axis=1)
            success = True
            feedback = "✅ Total intensity normalization applied. Each sample has been rescaled so abundance stays proportionate."

        elif method == "quantile":
            rank_means = (
                df[relevant_cols]
                .stack()
                .groupby(df[relevant_cols].rank(method="first").stack().astype(int))
                .mean()
            )
            ranks = df[relevant_cols].rank(method="min").stack().astype(int)
            df[relevant_cols] = ranks.map(rank_means).unstack()
            success = True
            feedback = "✅ Quantile normalization applied. The distributions have been forced into suspiciously elegant agreement."

        elif method == "reference_sample":
            reference = df[relevant_cols].median()
            df[relevant_cols] = df[relevant_cols].subtract(reference)
            success = True
            feedback = "✅ Reference sample normalization applied. The data now bows politely to a common baseline."

        elif method == "zscore":
            std = df[relevant_cols].std().replace(0, np.nan)
            df[relevant_cols] = (df[relevant_cols] - df[relevant_cols].mean()) / std
            success = True
            feedback = "✅ Z-score normalization applied. The intensities have been standardized into statistically respectable behavior."

        elif method == "vsn":
            df[relevant_cols] = np.log2(df[relevant_cols].clip(lower=0) + 1.0)
            success = True
            feedback = "✅ VSN-like normalization applied. The dynamic range has been calmed before it could do anything theatrical."

        else:
            success = False
            feedback = f"⚠️ Unknown normalization method {method}. The station declines to perform undocumented rituals."

        if success:
            imgs.extend(
                histogram_compare(
                    before_df=df_before,
                    after_df=df,
                    cols=relevant_cols,
                    title_before="Distribution Before Normalization",
                    title_after=f"Distribution After {method} Normalization",
                    bins=50,
                )
            )

    except Exception as e:
        success = False
        feedback = f"⚠️ Normalization failed: {str(e)}. The samples resisted alignment."

    return {
        "success": success,
        "num_pro": num_pro,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": 0,
        "dataset": df if success else dataset,
    }


def _simulate_imputer(dataset: dict, params: dict, visited_stations: set) -> dict:
    """
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
    """
    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Imputation cannot begin until spectral search has produced something missing in the first place. Right now you are repairing imaginary gaps.",
            "score": 0,
            "dataset": dataset,
        }

    method = str(params.get("imputation_method", "none")).lower()

    # Check if dataset is None or empty
    if dataset is None or dataset.empty:
        return {
            "success": False,
            "num_pro": None,
            "num_pep": None,
            "feedback": "⚠️ No dataset detected. The imputer searched for missing values and found only existential emptiness.",
            "img": [],
            "score": 0,
            "dataset": pd.DataFrame(),
        }

    relevant_cols = COND_A + COND_B

    df = dataset.copy()

    success = False
    feedback = None
    imgs = []

    # Sanity check - are relevant columns present in the dataset?
    if not relevant_cols or not all(col in dataset.columns for col in relevant_cols):
        return {
            "success": False,
            "num_pro": None,
            "num_pep": None,
            "feedback": "⚠️ No usable intensity columns found. Even the most determined imputer refuses to invent measurements from pure metadata.",
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
    def impute_matrix(x: pd.DataFrame, method: str) -> pd.DataFrame:

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
                estimator=LinearRegression(), random_state=42, max_iter=15
            )
        elif method == "randomforest":
            imputer = IterativeImputer(
                estimator=RandomForestRegressor(
                    n_estimators=200, random_state=42, n_jobs=-1
                ),
                random_state=42,
                max_iter=10,
            )
        elif method == "bayesian":
            imputer = IterativeImputer(
                estimator=BayesianRidge(),
                sample_posterior=True,
                random_state=42,
                max_iter=15,
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
                out.loc[miss, col] = rng.normal(
                    mu - 1.8 * sigma, 0.3 * sigma, size=miss.sum()
                )
            return out
        else:
            raise ValueError(f"Unknown imputation method: {method}")

        arr = imputer.fit_transform(x)
        return pd.DataFrame(arr, index=x.index, columns=x.columns)

    feedback_by_method = {
        "none": "✅ No imputation applied. The missing values remain exactly where the universe misplaced them.",
        "mean": "✅ Mean imputation applied. The gaps have been patched with averages and a moderate amount of statistical optimism.",
        "median": "✅ Median imputation applied. The missing values have been replaced with something sturdier than hope.",
        "knn": "✅ KNN imputation applied. Nearby values were consulted and, against all odds, gave advice.",
        "regression": "✅ Regression imputation applied. The missing values have been reconstructed from patterns the data swears were always there.",
        "randomforest": "✅ Random forest imputation applied. A small committee of trees has guessed the missing values with suspicious confidence.",
        "bayesian": "✅ Bayesian imputation applied. Probability has been invoked, uncertainty acknowledged, and the gaps reluctantly filled.",
        "minprob": "✅ MinProb imputation applied. Low-intensity values were summoned from the statistical underworld to occupy the blanks.",
    }
    imgs = []
    try:
        x_new = impute_matrix(x, method)
        df_new = df.copy()
        df_new[relevant_cols] = x_new

        imgs.append(
            imputer_before_after_stripgrid(
                before_df=x,
                after_df=x_new,
                cond_a_cols=COND_A,
                cond_b_cols=COND_B,
                title=f"Before vs After Imputation ({method})",
            )
        )

        success = True
        feedback = feedback_by_method.get(
            method, f"Imputation method '{method}' applied."
        )

        success = True
        feedback = feedback_by_method.get(
            method, f"Imputation method '{method}' applied."
        )
    except Exception as e:
        df_new = df.copy()
        success = False
        feedback = f"⚠️ Imputation failed: {str(e)}. The missing values remain missing and perhaps a little smug about it."

    return {
        "success": success,
        "num_prot": int(df_new[PROTEIN].nunique()),
        "num_pep": int(df_new[TOT_PEP].sum()),
        "feedback": feedback,
        "img": imgs,
        "score": 0,
        "dataset": df_new,
    }


def _simulate_multiple_testing_corrector(
    dataset: pd.DataFrame, params: dict, visited_stations: set
) -> dict:

    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "You need data before you can perform this step!",
            "score": 0,
            "dataset": dataset,
        }

    method = params.get("correction_method", "bh")
    success = False
    imgs = []
    score = 0

    # Handle missing dataset
    if dataset is None or dataset.empty:
        return {
            "success": success,
            "num_pro": None,
            "num_pep": None,
            "feedback": "☣️🧪 You reach for your dataset… but there's nothing. Bold strategy - fighting Proteome Collapse Syndrome without any data.",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame(),
        }
    else:
        df = dataset.copy()
        num_pro = int(dataset[PROTEIN_ID].nunique())
        num_pep = int(dataset[TOT_PEP].sum())

    # Handle missing p-value column
    if PVALUE not in df.columns:
        return {
            "success": success,
            "num_pro": num_pro,
            "num_pep": num_pep,
            "feedback": "⚠️ No p-values found. The experiment loses its grip on significance.",
            "img": imgs,
            "score": score,
            "dataset": df,
        }

    pvals = df[PVALUE].values

    print("running multiple testing correction with method:", method)

    try:
        if method == "bh":
            adjusted = multipletests(pvals, method="fdr_bh")
            df[PVALUE] = adjusted[1]
            success = True
            score = 10
            feedback = "📊 Benjamini-Hochberg activated. False discoveries are brought under control."
        elif method == "bt":
            adjusted = multipletests(pvals, method="fdr_by")
            df[PVALUE] = adjusted[1]
            success = True
            score = 12
            feedback = "🧠 Benjamini-Tekutieli engaged. Even chaotic dependencies are contained."
        elif method == "storey":
            qvals = _py_qvalue(pvals)["qvalues"]
            df[PVALUE] = qvals
            success = True
            score = 15
            feedback = "🔮 Storey q-values invoked. The hidden structure of truth is estimated."
        elif method == "bonferroni":
            adjusted = multipletests(pvals, method="bonferroni")
            df[PVALUE] = adjusted[1]
            success = True
            score = 6
            feedback = "🧨 Bonferroni applied. False positives are eliminated — along with most of your discoveries."
        elif method == "holm":
            adjusted = multipletests(pvals, method="holm")
            df[PVALUE] = adjusted[1]
            success = True
            score = 9
            feedback = "⚖️ Holm-Bonferroni engaged. Order is restored more gracefully."
        else:
            success = False
            score = 0
            feedback = "⚠️ Unknown correction method. Statistical defenses not deployed."

    except Exception:
        success = False
        score = 0
        feedback = "💥 Correction failed. The proteome resists statistical control."

    if success and PVALUE in df.columns:
        imgs.extend(mtc_histograms(df, value_col=PVALUE, species_col=ORGANISM))

    return {
        "success": success,
        "num_pro": num_pro,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": score,
        "dataset": df,
    }


def _simulate_the_cutter(
    dataset: pd.DataFrame, params: dict, visited_stations: set
) -> dict:

    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ The cutter remains sheathed until spectral search and downstream analysis have produced something worth slicing. Right now you are applying thresholds to wishful thinking.",
            "score": 0,
            "dataset": dataset,
        }

    fc = float(params.get("fold_change_cutoff", 1))
    pval = float(params.get("pvalue_cutoff", 0.05))
    dataset = dataset.copy() if dataset is not None else pd.DataFrame()
    imgs = []
    if FC not in dataset.columns:
        return {
            "summary": "Dataset missing required columns for cutter station.",
            "success": False,
            "score": 0,
            "cutoffs": {"log2FC": fc, "FDR": pval},
            "dataset": dataset,
            "feedback": "⚠️ No fold-change column found. The cutter cannot separate signal from noise without something sharp to work with.",
            "img": imgs,
            "true_positives": 0,
            "false_positives": 0,
            "final_hits": 0,
        }
    significant = dataset.loc[dataset[FC].abs() >= fc]
    if PVALUE in dataset.columns:
        significant = significant.loc[significant[PVALUE] <= pval]

    imgs.append(plot_significant_proteins(significant))

    return {
        "summary": "Final candidate selection complete.",
        "score": 0,
        "cutoffs": {"log2FC": fc, "FDR": pval},
        "dataset": significant,
        "feedback": f"✅ Candidate selection complete. You identified {len(significant)} proteins worthy of surviving the cutoffs, while the rest were quietly returned to statistical oblivion.",
        "img": imgs,
    }


def _simulate_veit(dataset: pd.DataFrame, params: dict, visited_stations: set) -> dict:
    imgs = []
    if dataset is None or dataset.empty:
        return {
            "success": False,
            "feedback": "⚠️ No final candidate set detected. Veit arrived ready to judge the outcome and found only the ceremonial remains of a pipeline.",
            "score": 0,
            "dataset": pd.DataFrame(),
            "true_positives": 0,
            "false_positives": 0,
            "img": imgs,
        }
    significant = dataset.copy()
    true_yeast = significant.query(f"{ORGANISM} == 'Yeast' and {FC} < 0")
    true_ecoli = significant.query(f"{ORGANISM} == 'E. coli' and {FC} > 0")
    false_yeast = significant.query(f"{ORGANISM} == 'Yeast' and {FC} >= 0")
    false_ecoli = significant.query(f"{ORGANISM} == 'E. coli' and {FC} <= 0")
    false_human = significant.query(f"{ORGANISM} == 'Human'")

    true_positives = len(true_yeast) + len(true_ecoli)
    false_positives = len(false_yeast) + len(false_ecoli) + len(false_human)
    score = (
        true_positives * (1 - false_positives / len(significant))
        if len(significant) > 0
        else 0
    )
    imgs.append(plot_scores(true_positives, false_positives))

    return {
        "success": True,
        "feedback": "✅ You made it to Veit. Against all reasonable expectation, the pipeline held together, the result is interpretable, and the lab may proceed with confidence and only minimal existential damage.",
        "score": score,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "dataset": dataset,
        "img": imgs,
    }


def _simulate_statistical_analysis(
    dataset: pd.DataFrame, params: dict, visited_stations: set
) -> dict:

    if "spectral_search" not in visited_stations:
        return {
            "success": False,
            "feedback": "⚠️ Statistical analysis is unavailable until spectral search has produced data worth interrogating. At the moment you are testing hypotheses against fog.",
            "score": 0,
            "dataset": dataset,
        }

    test = params.get("statistical_test", "none")
    success = False
    imgs = []
    score = 0

    # Handle missing dataset
    if dataset is None or dataset.empty:
        return {
            "success": success,
            "num_pro": None,
            "num_pep": None,
            "feedback": "⚠️ No dataset detected. The statistical machinery assembled itself magnificently and then had nothing to analyze.",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame(),
        }
    else:
        df = dataset.copy()
        num_pro = int(dataset[PROTEIN_ID].nunique())
        num_pep = int(dataset[TOT_PEP].sum())

    # Handle Missing Columns
    required_cols = COND_A + COND_B + [PROTEIN]
    if any(col not in df.columns for col in required_cols):
        return {
            "success": False,
            "num_pro": num_pro,
            "num_pep": num_pep,
            "feedback": "⚠️ Required columns are missing. The test cannot proceed without actual measurements to argue over.",
            "img": imgs,
            "score": score,
            "dataset": df,
        }

    try:
        expr = df[COND_A + COND_B].apply(pd.to_numeric, errors="coerce")
        # Replace ±inf (e.g. log(0)) with NaN so dropna() removes them before tests
        expr = expr.replace([np.inf, -np.inf], np.nan)

        # Compute log2 fold-change: log2(mean condition B / mean condition A)
        mean_a = expr[COND_A].mean(axis=1, skipna=True)
        mean_b = expr[COND_B].mean(axis=1, skipna=True)
        df[FC] = mean_b - mean_a

        p_values = np.full(len(expr), np.nan)

        if test == "welch":
            for idx in range(len(expr)):
                row = expr.iloc[idx]
                a = row[COND_A].dropna()
                b = row[COND_B].dropna()

                if len(a) < 2 or len(b) < 2:
                    p = np.nan
                else:
                    _, p = ttest_ind(a, b, equal_var=False, nan_policy="omit")
                p_values[idx] = p
            success = True
            feedback = "✅ Welch's t-test applied. Unequal variances were acknowledged and the proteins were judged accordingly."

        elif test == "limma":
            raise NotImplementedError("Limma not implemented")

        elif test == "mannwhitneyu":
            for idx in range(len(expr)):
                row = expr.iloc[idx]
                a = row[COND_A].dropna()
                b = row[COND_B].dropna()

                if len(a) == 0 or len(b) == 0:
                    p_values[idx] = np.nan
                    continue

                try:
                    _, p = mannwhitneyu(a, b, alternative="two-sided", method="exact")
                    p_values[idx] = p
                except ValueError:
                    _, p = mannwhitneyu(
                        a, b, alternative="two-sided", method="asymptotic"
                    )
                    p_values[idx] = p
            success = True
            feedback = "✅ Mann-Whitney U test applied. The samples were compared without assuming the universe had behaved normally."

        elif test == "permutation":
            N_PERMUTATIONS = 1000
            for idx in range(len(expr)):
                row = expr.iloc[idx]
                A = row[COND_A].dropna().values
                B = row[COND_B].dropna().values

                if len(A) == 0 or len(B) == 0:
                    p_values[idx] = np.nan
                    continue

                def statistic(x, y):
                    return np.mean(y) - np.mean(x)

                res = permutation_test(
                    (A, B),
                    statistic,
                    vectorized=False,
                    n_resamples=N_PERMUTATIONS,
                    alternative="two-sided",
                    random_state=42,
                )
                p = max(res.pvalue, 1 / (N_PERMUTATIONS + 1))
                p_values[idx] = p

            success = True
            feedback = f"✅ Permutation test applied ({N_PERMUTATIONS} permutations). Chance was consulted repeatedly until it gave a usable answer."
        else:
            success = False
            feedback = "⚠️ Unknown statistical test. The station declines to perform inferential improv theatre."

        df[PVALUE] = p_values

        if success:
            volcano_img = volcano_plot(
                df,
                title="Volcano Plot",
                p_val_col=PVALUE,
                fc_col=FC,
            )
            if volcano_img is not None:
                imgs.append(volcano_img)

    except Exception:
        success = False
        feedback = "⚠️ Statistical analysis failed. The proteome objected to formal questioning and descended into chaos."

    return {
        "success": success,
        "num_pro": num_pro,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": score,
        "dataset": df,
    }


STATION_SIMULATORS.update(
    {
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
        # ...
    }
)
"""Additional station simulators can be added to the STATION_SIMULATORS dict following the same pattern.
The key MUST correspond to the station_id used in the frontend configuration (frontend/src/assets/stations.json),
and the value is a function that takes (dataset, params) and returns a dict with results."""
