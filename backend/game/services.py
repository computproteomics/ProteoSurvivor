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
from .helper_functions import tr_boxplot, sp_scatterplot, mtc_histograms, imputer_before_after_swarmgrid
from statsmodels.stats.multitest import multipletests 
from qvalue import qvalue

from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from sklearn.ensemble import RandomForestRegressor

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
    # TODO: Add check to see if sample prep + MS was done previously
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
    matching_rows = file_map[file_map["key"] == file_key]
    if matching_rows.empty:
        raise ValueError(f"No data file found for parameters: {params}")
    data_file_name = matching_rows.iloc[0]["ParameterSet"] + ".tsv"

    # Load the corresponding data file and extract results
    dataset = pandas.read_csv(f"data/{data_file_name}", sep="\t")

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
        for species in dataset["Organism"].unique():

            count_cols_a = [
                "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_01 Total Spectral Count",
                "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_02 Total Spectral Count",
                "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_03 Total Spectral Count",
            ]
            int_cols_a = [
                "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_01 Intensity",
                "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_02 Intensity",
                "LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_03 Intensity",
            ]
            count_cols_b = [
                "LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_01 Total Spectral Count",
                "LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_02 Total Spectral Count",
                "LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_03 Total Spectral Count",
            ]
            int_cols_b = [
                "LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_01 Intensity",
                "LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_02 Intensity",
                "LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_03 Intensity",
            ]

            # Make a vector of all count_cols_a columns into one column "Total Spectral Count A"
            spec_a = np.log2(np.concatenate([dataset[c].values for c in count_cols_a]))
            spec_b = np.log2(np.concatenate([dataset[c].values for c in count_cols_b]))

            int_a = np.log2(np.concatenate([dataset[c].values for c in int_cols_a]))
            int_b = np.log2(np.concatenate([dataset[c].values for c in int_cols_b]))

            tr_scatter = sp_scatterplot(
                x=spec_a,
                y=int_a,
                x_col="Total Spectral Count A",
                y_col="log2(Intensity A)",
                color=species_palette[species],
                title=f"Spectral Count vs Intensity for {species} - Condition A",
            )
            imgs.append(tr_scatter)
            tr_scatter = sp_scatterplot(
                x=spec_b,
                y=int_b,
                x_col="Total Spectral Count B",
                y_col="log2(Intensity B)",
                color=species_palette[species],
                title=f"Spectral Count vs Intensity for {species} - Condition B",
            )
            imgs.append(tr_scatter)

        success = True
        feedback = None

    except Exception as e:
        success = False
        feedback = f"Error plotting spectra counts: {str(e)}"

    return {
        "success": success,
        "dataset": dataset,
        "num_prot": int(dataset["Protein ID"].nunique()),
        "num_pep": int(dataset["Combined Total Peptides"].sum()),
        "img": imgs,
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
    success = False
    imgs = []
    score = 0
    
    # Handle missing dataset
    if dataset is None:
        return {
            "success": success,
            "num_prot": None,
            "num_pep": None,
            "feedback": "No dataset available. Cannot perform transformation. Have you forgotten a previous step?",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame()
        }
    else:
        df = dataset.copy()
        num_prot = int(dataset["Protein ID"].nunique())
        num_pep = int(dataset["Combined Total Peptides"].sum())

    relevant_cols = [col for col in df.columns if col.endswith("MaxLFQ Intensity")]
    
    try:
        img_before = tr_boxplot(
            df, relevant_cols, title="Intensities Before Transformation"
        )
        imgs.append(img_before)

        if method == "none":
            success = True
            feedback = "No transformation applied. Data remains unchanged."

        elif method == "log2":
            df[relevant_cols] = np.log2(df[relevant_cols])
            img_after = tr_boxplot(
                df, relevant_cols, title="Intensities After Transformation (Log2)"
            )
            imgs.append(img_after)
            success = True
            feedback = "Log2 transformation applied. Variance stabilized for downstream analysis."

        elif method == "ln":
            df[relevant_cols] = np.log(df[relevant_cols])
            img_after = tr_boxplot(
                df,
                relevant_cols,
                title="Intensities After Transformation (Natural Log)",
            )
            imgs.append(img_after)
            success = True
            feedback = "Natural log transformation applied. Variance stabilized for downstream analysis."

    except Exception as e:
        success = False
        feedback = f"Error applying transformation: {str(e)}"

    return {
        "success": success,
        "num_pro": num_prot,
        "num_pep": num_pep,
        "feedback": feedback,
        "img": imgs,
        "score": 0,
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
    """""

    method = str(params.get("imputation_method", "none")).lower()

    # Check if dataset is None or empty
    if dataset is None or dataset.empty:
        return {
            "success": False,
            "num_pro": None,
            "num_pep": None,
            "feedback": "No dataset available. Cannot perform imputation. Have you forgotten to do spectral search?",
            "img": [],
            "score": 0,
            "dataset": pd.DataFrame()
        }

    relevant_cols = COND_A + COND_B

    df = dataset.copy()

    imgs: list[str] = []
    success = False
    feedback = None
    
    # Sanity check - are relevant columns present in the dataset?
    if not relevant_cols or not all(col in dataset.columns for col in relevant_cols):
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
        .apply(pandas.to_numeric, errors="coerce")
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

        imgs.append(
            imputer_before_after_swarmgrid(
                before_df=x,
                after_df=x_new,
                cond_a_cols=COND_A,
                cond_b_cols=COND_B,
                title=f"Before vs After Imputation ({method})",
            )
        )

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
            "feedback": "No dataset available. Cannot perform multiple testing correction. Have you forgotten a previous step?",
            "img": imgs,
            "score": score,
            "dataset": pd.DataFrame()
        }
    else:
        df = dataset.copy()
        num_prot = int(dataset["Protein ID"].nunique())
        num_pep = int(dataset["Combined Total Peptides"].sum())

    p_val_col = "p_value"

    # Handle missing p-value column
    if p_val_col not in df.columns:
        return {
            "success": success,
            "num_prot": num_prot,
            "num_pep": num_pep,
            "feedback": f"Column '{p_val_col}' not found in dataset. Cannot perform multiple testing correction. Have you forgotten a previous step?",
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
            mtc_histograms(
                df,
                value_col="p_adjusted",
                species_col="Organism"
            )
        )

    return {
        "success": success,
        "num_prot": num_prot,
        "num_pep": num_pep,
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


def _simulate_veit(dataset: Any, params: dict) -> dict:
    score = random.randint(70, 100)

    return {
        "success": True,
        "feedback": "You made it to Veit. The pipeline held together, the result is interpretable, and the lab can move forward with confidence.",
        "score": score,
        "dataset": dataset,
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
