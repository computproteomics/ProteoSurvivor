"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""

import random
from typing import Any, cast
import pandas as pd
from .models import StationRun, CutterStationResult
import numpy as np
import os
from .serializers import DataFrameSessionSerializer
from .helper_functions import (
    tr_boxplot,
    sp_scatterplot,
    mtc_histograms,
    _create_histogram,
    plot_significant_proteins
)
from statsmodels.stats.multitest import multipletests
from qvalue import qvalue

from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from sklearn.ensemble import RandomForestRegressor

from scipy.stats import ttest_ind, mannwhitneyu, permutation_test

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
P_VALUE_COL = "p_value"
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

    result = runner(dataset, params)
    print(f"Simulation result for station '{station_id}': {result}")
    if result.get("success"):
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
        if station_id == "the_cutter":
            cutter_result = CutterStationResult(
                station_run=run,
                true_positives=result.get("true_positives", 0),
                false_positives=result.get("false_positives", 0),
            )
            cutter_result.save()
            print(f"Saved CutterStationResult for StationRun ID {run.id}")

    request.session["current_dataset"] = DataFrameSessionSerializer.dumps(
        result.get("dataset", dataset)
    )
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
    # TODO: Add check to see if sample prep was done previously
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
            "feedback": "Unfortunately, we do not have a data search result for this set of parameters.",
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


def _simulate_transform(dataset: pd.DataFrame, params: dict) -> dict:
    method = params.get("transform_method", "none")
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

    relevant_cols = [col for col in df.columns if col.endswith("MaxLFQ Intensity")]

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
            feedback = "Log2 applied. The wild intensities have been domesticated."
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
            feedback = "Your data has been gently persuaded into natural log space."
            score = 10

        else:
            success = False
            feedback = "Unknown transformation method. The proteome looks confused."

    except Exception:
        success = False
        feedback = "⚠️🧪 Transformation failed. The proteome destabilizes — something in your data cannot survive the logarithm. Did you prepare it properly?"

    return {
        "success": success,
        "num_pro": num_pro,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": score,
        "dataset": df,
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
    """ ""

    method = str(params.get("imputation_method", "none")).lower()
    if dataset is None:
        df = pd.DataFrame()
    else:
        df = dataset.copy()

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
        feedback = feedback_by_method.get(
            method, f"Imputation method '{method}' applied."
        )
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
        "dataset": df_new,
    }


def _simulate_multiple_testing_corrector(dataset: pd.DataFrame, params: dict) -> dict:
    method = params.get("correction_method", "none")
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
    if P_VALUE_COL not in df.columns:
        return {
            "success": success,
            "num_pro": num_pro,
            "num_pep": num_pep,
            "feedback": "⚠️ No p-values found. The experiment loses its grip on significance.",
            "img": imgs,
            "score": score,
            "dataset": df,
        }

    pvals = df[P_VALUE_COL].values

    try:
        if method == "bh":
            adjusted = multipletests(pvals, method="fdr_bh")
            df[P_VALUE_COL] = adjusted[1]
            success = True
            score = 10
            feedback = "📊 Benjamini-Hochberg activated. False discoveries are brought under control."
        elif method == "bt":
            adjusted = multipletests(pvals, method="fdr_by")
            df[P_VALUE_COL] = adjusted[1]
            success = True
            score = 12
            feedback = "🧠 Benjamini-Tekutieli engaged. Even chaotic dependencies are contained."
        elif method == "storey":
            qvals = qvalue(pvals)
            df[P_VALUE_COL] = qvals
            success = True
            score = 15
            feedback = "🔮 Storey q-values invoked. The hidden structure of truth is estimated."
        elif method == "bonferroni":
            adjusted = multipletests(pvals, method="bonferroni")
            df[P_VALUE_COL] = adjusted[1]
            success = True
            score = 6
            feedback = "🧨 Bonferroni applied. False positives are eliminated — along with most of your discoveries."
        elif method == "holm":
            adjusted = multipletests(pvals, method="holm")
            df[P_VALUE_COL] = adjusted[1]
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

    if success and P_VALUE_COL in df.columns:
        imgs.extend(mtc_histograms(df, value_col=P_VALUE_COL, species_col=ORGANISM))

    return {
        "success": success,
        "num_pro": num_pro,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": score,
        "dataset": df,
    }


def _simulate_the_cutter(dataset: pd.DataFrame, params: dict) -> dict:
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
            "feedback": f"The dataset must contain {FC} columns for the cutter station to function properly.",
            "img": imgs,
            "true_positives": 0,
            "false_positives": 0,
            "final_hits": 0,
        }
    significant = dataset.loc[dataset[FC].abs() >= fc]
    if PVALUE in dataset.columns:
        significant = significant.loc[significant[PVALUE] <= pval]
    true_yeast = significant.query(f"{ORGANISM} == 'Yeast' and {FC} < 0")
    true_ecoli = significant.query(f"{ORGANISM} == 'E. coli' and {FC} > 0")
    false_yeast = significant.query(f"{ORGANISM} == 'Yeast' and {FC} >= 0")
    false_ecoli = significant.query(f"{ORGANISM} == 'E. coli' and {FC} <= 0")
    false_human = significant.query(f"{ORGANISM} == 'Human'")

    true_positives = len(true_yeast) + len(true_ecoli)
    false_positives = len(false_yeast) + len(false_ecoli) + len(false_human)
    score = true_positives * (1 - false_positives / len(significant)) if len(significant) > 0 else 0
    final_hits = len(significant)
    imgs.append(plot_significant_proteins(significant))

    return {
        "summary": "Final candidate selection complete.",
        "true_positives": true_positives,
        "false_positives": false_positives,
        "final_hits": final_hits,
        "success": true_positives > 0,
        "score": score,
        "cutoffs": {"log2FC": fc, "FDR": pval},
        "dataset": significant,
        "feedback": f"You identified {final_hits} significant candidates with the given cutoffs. Among them, {true_positives} are true positives (correctly identified yeast or E. coli proteins) and {false_positives} are false positives (incorrectly identified human proteins or misclassified yeast/E. coli). Your score reflects the balance between maximizing true positives and minimizing false positives.",
        "img": imgs,
    }


def _simulate_veit(dataset: Any, params: dict) -> dict:
    score = random.randint(70, 100)

    return {
        "success": True,
        "feedback": "You made it to Veit. The pipeline held together, the result is interpretable, and the lab can move forward with confidence.",
        "score": score,
        "dataset": dataset,
    }


def _simulate_statistical_analysis(dataset: pd.DataFrame, params: dict) -> dict:
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
            "feedback": "☣️🧪 You reach for your dataset… but there's nothing. Bold strategy - fighting Proteome Collapse Syndrome without any data.",
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
            "feedback": "⚠️ Required columns are missing. The statistical test cannot be performed.",
            "img": imgs,
            "score": score,
            "dataset": df,
        }
    
    try:
        expr = df[COND_A + COND_B].copy()
        p_values = np.full(len(expr), np.nan)

        if test == "welch":
            for idx, protein in enumerate(expr.index):
                row = expr.iloc[idx]
                a = pd.to_numeric(row[COND_A], errors="coerce").dropna()
                b = pd.to_numeric(row[COND_B], errors="coerce").dropna()

                if len(a) == 0 or len(b) == 0:
                    p = np.nan
                else:
                    _, p = ttest_ind(a, b, equal_var=False, nan_policy="omit")
                p_values[idx] = p
            success = True
            feedback = "Welch's t-test applied."

        elif test == "limma":
            raise NotImplementedError("Limma not implemented")
               
        elif test == "mannwhitneyu":
            for idx, protein in enumerate(expr.index):
                row = expr.iloc[idx]
                a = pd.to_numeric(row[COND_A], errors="coerce").dropna()
                b = pd.to_numeric(row[COND_B], errors="coerce").dropna()

                if len(a) == 0 or len(b) == 0:
                    p_values[idx] = np.nan
                    continue

                try:
                    _, p = mannwhitneyu(
                        a,
                        b,
                        alternative="two-sided",
                        method="exact"
                    )
                    p_values[idx] = p
                except ValueError:
                    _, p = mannwhitneyu(
                        a,
                        b,
                        alternative="two-sided",
                        method="asymptotic"
                    )
                    p_values[idx] = p
            success = True
            feedback = "Mann-Whitney U test applied."
        
        elif test == "permutation":
            N_PERMUTATIONS = 1000
            for idx, protein in enumerate(expr.index):
                row = expr.iloc[idx]
                A = pd.to_numeric(row[COND_A], errors="coerce").dropna().values
                B = pd.to_numeric(row[COND_B], errors="coerce").dropna().values

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
                    random_state=42
                )
                p = max(res.pvalue, 1 / (N_PERMUTATIONS + 1))
                p_values[idx] = p

            success = True
            feedback = f"Permutation test applied ({N_PERMUTATIONS} permutations)."
        else:
            success = False
            feedback = "Unknown statistical test."

        if len(p_values) > 0:
            df[P_VALUE_COL] = pd.Series(p_values, index=df.index)
        
    except Exception:
        success = False
        feedback = "Error applying statistical test. The proteome descends into chaos."

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
        "imputer": _simulate_normalize,
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
