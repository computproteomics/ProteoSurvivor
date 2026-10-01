"""
Game logic: scoring, answer evaluation, and proteomics station simulations.
"""

import random
from pathlib import Path
from typing import Any, cast
import pandas as pd
from .models import StationRun, FinalStationResult
import numpy as np
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

try:
    from py_qvalue import qvalue as _py_qvalue
except Exception:
    _py_qvalue = None

from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from sklearn.ensemble import RandomForestRegressor

from scipy.special import digamma, polygamma
from scipy.stats import t as t_dist
from scipy.stats import ttest_ind, mannwhitneyu

from django.conf import settings

# Absolute path to the backend data directory, resolved relative to this file
# so it works regardless of the process working directory (development or Docker).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

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
HUMAN = "Homo sapiens"
YEAST = "Yeast"
ECOLI = "E. coli"
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
HIGH_CONFIDENCE_PROTEIN_PROBABILITY = 0.99
SIGNIFICANCE_THRESHOLD = 0.05

DATA_REVIEW_COLUMN_EXPLANATIONS = {
    PROTEIN: "Protein group label reported by the search engine for this row.",
    PROTEIN_ID: "Stable identifier for the leading protein in the group.",
    ENTRY: "Database entry name used to map the hit back to the reference proteome.",
    GENE: "Gene symbol connected to the matched protein entry.",
    ORGANISM: "Species assignment for the protein group. Useful for spotting host/background contamination or biology.",
    TOT_PEP: "Number of identified peptides supporting this protein group. Single-peptide hits are often less convincing.",
    SPEC_COUNT: "How many spectra were assigned to this protein. Larger counts usually indicate stronger evidence.",
    PROBABILITY: "Protein-level confidence score from the search workflow. Higher values mean the identification is more trustworthy.",
    PVALUE: "Statistical evidence against no difference between conditions. Smaller values indicate stronger support.",
    FC: "Estimated abundance change between conditions. Larger absolute values indicate stronger regulation.",
}


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


def _format_metric_value(
    value: Any,
    *,
    digits: int = 2,
    as_percent: bool = False,
    for_display: bool = True,
) -> str | float | None:
    """Normalize metric values for either frontend display strings or numeric JSON fields."""
    if value is None:
        return "n/a" if for_display else None

    try:
        float_value = float(value)
    except (TypeError, ValueError):
        return "n/a" if for_display else None

    if not np.isfinite(float_value):
        return "n/a" if for_display else None

    rounded = round(float_value, digits)
    if not for_display:
        return rounded

    if as_percent:
        return f"{rounded:.{digits}f}%"

    if rounded == int(rounded):
        return f"{int(rounded):,}"

    return f"{rounded:,.{digits}f}"


def _simulate_data_review(dataset: pd.DataFrame | None, params: dict) -> dict:
    """Summarize the current working dataset so players can inspect it before downstream analysis."""
    del params  # data review is intentionally parameter-free

    if dataset is None or dataset.empty:
        return {
            "success": False,
            "summary": "No protein table is available yet.",
            "feedback": "⚠️ Run spectral search first so there is an actual dataset to inspect.",
            "score": 0,
            "dataset": pd.DataFrame(),
        }

    df = dataset.copy()
    intensity_columns = [column for column in COND_A + COND_B if column in df.columns]
    intensity_values = None
    if intensity_columns:
        intensity_values = df[intensity_columns].replace([np.inf, -np.inf], np.nan)
    total_measurements = int(intensity_values.size) if intensity_values is not None else 0
    missing_cells = (
        int(intensity_values.isna().sum().sum())
        if intensity_values is not None and total_measurements
        else 0
    )
    missing_fraction = (
        (missing_cells / total_measurements) * 100 if total_measurements else None
    )
    # If the primary protein identifier column is unavailable, fall back to row count.
    proteins = int(df[PROTEIN_ID].nunique()) if PROTEIN_ID in df.columns else int(len(df))
    peptides = int(df[TOT_PEP].sum()) if TOT_PEP in df.columns else None
    one_peptide = (
        int((pd.to_numeric(df[TOT_PEP], errors="coerce") <= 1).sum())
        if TOT_PEP in df.columns
        else None
    )
    high_confidence = (
        int(
            (
                pd.to_numeric(df[PROBABILITY], errors="coerce")
                >= HIGH_CONFIDENCE_PROTEIN_PROBABILITY
            ).sum()
        )
        if PROBABILITY in df.columns
        else None
    )
    significant = (
        int((pd.to_numeric(df[PVALUE], errors="coerce") <= SIGNIFICANCE_THRESHOLD).sum())
        if PVALUE in df.columns
        else None
    )

    metric_cards = [
        {
            "label": "Proteins",
            "value": f"{proteins:,}",
            "description": "Unique protein groups currently carried through the workflow.",
        },
        {
            "label": "Identified peptides",
            "value": _format_metric_value(peptides, digits=0),
            "description": "Total peptide evidence supporting the current table.",
        },
        {
            "label": "Samples / replicates",
            "value": f"{len(intensity_columns)}",
            "description": "Intensity columns available for comparing conditions.",
        },
        {
            "label": "Missing intensity values",
            "value": _format_metric_value(missing_fraction, as_percent=True),
            "description": "High missingness can make downstream statistics unstable.",
        },
        {
            "label": "Single-peptide proteins",
            "value": _format_metric_value(one_peptide, digits=0),
            "description": "These hits can be less robust than proteins backed by multiple peptides.",
        },
        {
            "label": "High-confidence proteins",
            "value": _format_metric_value(high_confidence, digits=0),
            "description": f"Protein groups with probability ≥ {HIGH_CONFIDENCE_PROTEIN_PROBABILITY}.",
        },
    ]
    if significant is not None:
        metric_cards.append(
            {
                "label": "Significant proteins",
                "value": _format_metric_value(significant, digits=0),
                "description": f"Rows with p-value ≤ {SIGNIFICANCE_THRESHOLD} in the current table.",
            }
        )

    sample_metrics = []
    for column in intensity_columns:
        sample_series = pd.to_numeric(intensity_values[column], errors="coerce")
        sample_metrics.append(
            {
                "sample": column,
                "median_intensity": _format_metric_value(
                    sample_series.median(), for_display=False
                ),
                "min_intensity": _format_metric_value(
                    sample_series.min(), for_display=False
                ),
                "max_intensity": _format_metric_value(
                    sample_series.max(), for_display=False
                ),
                "missing_fraction": _format_metric_value(
                    sample_series.isna().mean() * 100, for_display=False
                ),
            }
        )

    organism_breakdown = []
    if ORGANISM in df.columns:
        organism_counts = df[ORGANISM].fillna("Unknown").value_counts()
        organism_breakdown = [
            {"organism": str(organism), "proteins": int(count)}
            for organism, count in organism_counts.items()
        ]

    table_columns = [str(column) for column in df.columns]
    table_rows = [
        [_to_json_safe(value) for value in row]
        for row in df.itertuples(index=False, name=None)
    ]

    column_explanations = [
        {"column": column, "explanation": explanation}
        for column, explanation in DATA_REVIEW_COLUMN_EXPLANATIONS.items()
        if column in df.columns
    ]
    if intensity_columns:
        column_explanations.append(
            {
                "column": "Sample intensity columns",
                "explanation": "These replicate intensity columns are the core quantitative measurements used for filtering, normalization, and statistics.",
            }
        )

    return {
        "success": True,
        "summary": f"Data review ready. Browse all {len(df):,} rows from the current protein table.",
        "feedback": (
            "Look for heavy missingness, unusually different sample medians, many single-peptide proteins, "
            "or species imbalances before committing to downstream preprocessing choices."
        ),
        "recommendation": "Use this station whenever you want to sanity-check how the table changed after filtering, normalization, imputation, or statistics.",
        "metric_cards": metric_cards,
        "sample_metrics": sample_metrics,
        "organism_breakdown": organism_breakdown,
        "column_explanations": column_explanations,
        "table_preview": {
            "columns": table_columns,
            "rows": table_rows,
            "shown_rows": int(len(df)),
            "total_rows": int(len(df)),
        },
        "score": 0,
        "dataset": df,
    }


def commit_pending_station_run(request) -> dict | None:
    """Persist the pending station run (if any) for the authenticated player.

    Called when the player returns to the map, the point after which the last
    station run can no longer be undone via "Adjust parameters". Anonymous
    players have nothing to attribute the run to, so pending data is discarded.
    """
    pending = request.session.pop("pending_station_run", None)
    if not pending or not request.user.is_authenticated:
        return None

    run = StationRun(
        player=request.user,
        station_id=pending["station_id"],
        params=pending.get("params", {}),
        score=pending.get("score", 0),
    )
    run.save()
    print(f"Saved StationRun with ID {run.id} for user {request.user.username}")

    if pending.get("final"):
        final_result = FinalStationResult(
            station_run=run,
            true_positives=pending.get("true_positives", 0),
            false_positives=pending.get("false_positives", 0),
        )
        final_result.save()
        print(f"Saved FinalStationResult for StationRun ID {run.id}")

    return {"station_id": run.station_id, "score": run.score}


def run_station(request, station_id: str, params: dict) -> dict[str, Any]:
    """
    Simulate the execution of a proteomics lab station with the given parameters.
    Returns a dictionary with the simulation results.
    """
    print(f"Running station '{station_id}' with parameters: {params}")

    # "Adjust parameters" re-runs the same station without re-entering it from the
    # map, so it must start from the dataset that existed before the prior run,
    # not from that run's own output. Re-entering the station (enter_station_view)
    # clears this tracking so a deliberate fresh run still uses the current dataset.
    if request.session.get("last_run_station_id") == station_id:
        dataset = request.session.get("pre_run_dataset", None)
    else:
        dataset = request.session.get("current_dataset", None)
        request.session["pre_run_dataset"] = dataset
        request.session["last_run_station_id"] = station_id
    if dataset is not None:
        dataset = DataFrameSessionSerializer.loads(dataset)
    runner = STATION_SIMULATORS.get(station_id)
    if runner is None:
        raise ValueError(f"Unknown station '{station_id}'.")

    result = runner(dataset, params)

    print(f"Simulation result for station '{station_id}': {result}")
    if result.get("success"):
        is_final = settings.STATIONS_CONFIG[station_id].get("final", False)
        if is_final:
            # The final station produces the definitive game result (score, TP/FP).
            # There is no "adjust and redo" to protect, and the leaderboard needs
            # it immediately, so save StationRun + FinalStationResult right away.
            run = StationRun(
                player=request.user,
                station_id=station_id,
                params=params,
                score=result.get("score", 0),
            )
            if request.user.is_authenticated:
                run.save()
                print(f"Saved StationRun with ID {run.id} for user {request.user.username}")
                final_result = FinalStationResult(
                    station_run=run,
                    true_positives=result.get("true_positives", 0),
                    false_positives=result.get("false_positives", 0),
                )
                final_result.save()
                print(f"Saved FinalStationResult for StationRun ID {run.id}")
        else:
            # "Adjust parameters" lets the player redo the same station, and the
            # previous attempt no longer survives in the dataset. Persisting the
            # run immediately would make an experiment that was reverted by a
            # re-run look permanent. Instead the run is stashed as "pending" in
            # the session and written to the database when the player exits the
            # station (commit_pending_station_run). A re-run simply overwrites
            # the pending record.
            request.session["pending_station_run"] = {
                "station_id": station_id,
                "params": params,
                "score": result.get("score", 0),
            }
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


def _simulate_sample_prep(dataset: dict, params: dict) -> dict:
    return {
        "success": True,
        "feedback": "✅ Sample preparation complete. Strangely, your peptides made it through intact despite improbable handling, questionable luck, and the general hostility of the universe.",
        "score": 0,
        "dataset": dataset,
    }


def _simulate_mass_spec(dataset: dict, params: dict) -> dict:

    return {
        "success": True,
        "feedback": "✅ Mass spectrometry complete. Somehow the peptides survived the ionization gauntlet and emerged as usable spectra.",
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
    file_map = pd.read_csv(DATA_DIR / "ParameterTable.csv")  # Mapping table
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
    if not (DATA_DIR / data_file_name).exists():
        return {
            "success": False,
            "feedback": "⚠️ No search result exists for this parameter combo. You have discovered a forbidden FragPipe timeline.",
            "score": 0,
            "dataset": dataset,
        }

    # Load the corresponding data file and extract results
    zeros = {col: "0" for col in COND_A + COND_B}
    dataset = pd.read_table(DATA_DIR / data_file_name, na_values=zeros)

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
        feedback = """
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
        """

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
        "feedback": feedback,
    }


def _simulate_transform(dataset: pd.DataFrame, params: dict) -> dict:

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


def _simulate_filtering(dataset: pd.DataFrame, params: dict) -> dict:

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


def _simulate_normalize(dataset: pd.DataFrame, params: dict) -> dict:

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
            values = df[relevant_cols].replace([np.inf, -np.inf], np.nan)
            std = values.std().replace(0, np.nan)
            df[relevant_cols] = (values - values.mean()) / std
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


def _simulate_imputer(dataset: dict, params: dict) -> dict:
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


def _simulate_multiple_testing_corrector(dataset: pd.DataFrame, params: dict) -> dict:

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
    valid_mask = np.isfinite(pvals)

    print("running multiple testing correction with method:", method)

    def _apply_correction(pvals_all, valid_mask, statsmodels_method):
        """Apply multipletests only to finite p-values; NaN positions remain NaN."""
        corrected = np.full(len(pvals_all), np.nan)
        if valid_mask.sum() > 0:
            adj = multipletests(pvals_all[valid_mask], method=statsmodels_method)
            corrected[valid_mask] = adj[1]
        return corrected

    try:
        if method == "bh":
            df[PVALUE] = _apply_correction(pvals, valid_mask, "fdr_bh")
            success = True
            score = 10
            feedback = "📊 Benjamini-Hochberg activated. False discoveries are brought under control."
        elif method == "bt":
            df[PVALUE] = _apply_correction(pvals, valid_mask, "fdr_by")
            success = True
            score = 12
            feedback = "🧠 Benjamini-Tekutieli engaged. Even chaotic dependencies are contained."
        elif method == "storey":
            if _py_qvalue is not None:
                corrected = np.full(len(pvals), np.nan)
                if valid_mask.sum() > 0:
                    corrected[valid_mask] = _py_qvalue(pvals[valid_mask])["qvalues"]
                df[PVALUE] = corrected
                success = True
                score = 15
                feedback = "🔮 Storey q-values invoked. The hidden structure of truth is estimated."
            else:
                # Fallback for environments where py-qvalue is unavailable (e.g. Python < 3.10).
                df[PVALUE] = _apply_correction(pvals, valid_mask, "fdr_bh")
                success = True
                score = 10
                feedback = "📊 Storey q-values unavailable in this Python environment; used Benjamini-Hochberg instead."
        elif method == "bonferroni":
            df[PVALUE] = _apply_correction(pvals, valid_mask, "bonferroni")
            success = True
            score = 6
            feedback = "🧨 Bonferroni applied. False positives are eliminated — along with most of your discoveries."
        elif method == "holm":
            df[PVALUE] = _apply_correction(pvals, valid_mask, "holm")
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
        "success": True,
        "score": 0,
        "cutoffs": {"log2FC": fc, "FDR": pval},
        "dataset": significant,
        "feedback": f"✅ Candidate selection complete. You identified {len(significant)} proteins worthy of surviving the cutoffs, while the rest were quietly returned to statistical oblivion.",
        "img": imgs,
    }


def _simulate_final_report(dataset: pd.DataFrame, params: dict) -> dict:
    imgs = []
    if dataset is None or dataset.empty:
        return {
            "success": False,
            "feedback": '⚠️ No final candidate set detected. The "Please Let This Be Significant" Lounge opened for business and found only ceremonial pipeline debris.',
            "score": 0,
            "dataset": pd.DataFrame(),
            "true_positives": 0,
            "false_positives": 0,
            "img": imgs,
        }
    significant = dataset.copy()
    if ORGANISM not in significant.columns or FC not in significant.columns:
        return {
            "success": False,
            "feedback": "⚠️ Final report requires Organism and fold_change columns. Please complete the statistical analysis step before submitting.",
            "score": 0,
            "dataset": significant,
            "true_positives": 0,
            "false_positives": 0,
            "img": imgs,
        }

    true_yeast = significant[(significant[ORGANISM] == YEAST) & (significant[FC] < 0)]
    true_ecoli = significant[
        (significant[ORGANISM] == ECOLI) & (significant[FC] > 0)
    ]
    false_yeast = significant[
        (significant[ORGANISM] == YEAST) & (significant[FC] >= 0)
    ]
    false_ecoli = significant[
        (significant[ORGANISM] == ECOLI) & (significant[FC] <= 0)
    ]
    false_human = significant[significant[ORGANISM] == HUMAN]

    true_positives = len(true_yeast) + len(true_ecoli)
    false_positives = len(false_yeast) + len(false_ecoli) + len(false_human)

    precision_denominator = true_positives + false_positives
    precision = (
        true_positives / precision_denominator if precision_denominator > 0 else 0
    )

    # Reward larger high-quality hit sets so tiny TP counts with zero FP are not optimal.
    tp_volume_factor = (
        true_positives / (true_positives + 10) if true_positives > 0 else 0
    )
    score = precision * tp_volume_factor
    min_fdr = 1e-3
    # Use min_fdr for FDR if FP == 0, otherwise calculate normally
    if precision_denominator > 0:
        fdr = (
            false_positives / precision_denominator if false_positives > 0 else min_fdr
        )
    else:
        fdr = None
    imgs.append(plot_scores(true_positives, false_positives, min_fdr=min_fdr))

    feedback = (
        '✅ You made it to The "Please Let This Be Significant" Lounge. '
        "Against all expectation, the pipeline held together and your report looks statistically defensible.<br/><br/>"
        "<strong>Final score breakdown</strong><br/>"
        f"TP = {true_positives}, FP = {false_positives}<br/>"
        "Precision = TP / (TP + FP)<br/>"
        f"= {true_positives} / ({true_positives} + {false_positives}) = {precision:.4f}<br/>"
        f"FDR = FP / (TP + FP) = {false_positives} / ({true_positives} + {false_positives}) = {fdr:.6f}<br/><br/>"
        "TP volume factor = TP / (TP + 10)<br/>"
        f"= {true_positives} / ({true_positives} + 10) = {tp_volume_factor:.4f}<br/><br/>"
        "Final score = Precision × TP volume factor<br/>"
        f"= {precision:.4f} × {tp_volume_factor:.4f} = <strong>{score:.4f}</strong><br/><br/>"
        "If high enough, you will see your score in the leaderboard and earn the respect of the proteome. If not, well... at least you made it here and learned something, and that's something to be proud of, right?"
    )

    return {
        "success": True,
        "feedback": feedback,
        "score": score,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "dataset": dataset,
        "img": imgs,
    }


def _trigamma_inv(y: float) -> float:
    """Return x such that trigamma(x) == y, using Newton's method.

    The starting approximation uses the asymptotic relation trigamma(x) ≈ 1/x,
    giving x₀ ≈ 1/y for large y (y > 0.5) and x₀ ≈ 1/(0.5y + 0.5) for small y (y ≤ 0.5).
    Clipped to 1e-10 to stay in the valid (positive) domain.
    Convergence is typically reached in fewer than 10 iterations; 50 is a
    generous safety limit.
    """
    _MAX_ITER = 50
    if not np.isfinite(y) or y <= 0:
        return np.nan
    # Starting approximation: trigamma(x) ≈ 1/x for large x
    x = max(0.5 + 1.0 / y if y > 0.5 else 1.0 / (0.5 * y + 0.5), 1e-10)
    for _ in range(_MAX_ITER):
        tri = float(polygamma(1, x))
        pent = float(polygamma(2, x))
        if pent == 0:
            break
        step = (tri - y) / pent
        x = max(x - step, 1e-10)
        if abs(step) < 1e-8:
            break
    return x


def _squeeze_var(
    sample_vars: np.ndarray, residual_dfs: np.ndarray
) -> tuple[np.ndarray, float]:
    """
    Empirical Bayes variance moderation following Smyth (2004) / limma squeezeVar.

    Fits a scaled inverse chi-squared prior to the per-protein sample variances and
    returns posterior (squeezed) variances together with the estimated prior degrees
    of freedom.  Proteins without an estimable variance (df == 0) are assigned the
    prior variance so they still receive a p-value.

    Parameters
    ----------
    sample_vars : ndarray, shape (n,)
        Per-protein pooled sample variance.  NaN where variance cannot be computed.
    residual_dfs : ndarray, shape (n,)
        Per-protein residual degrees of freedom (nA + nB - 2).
    """
    valid = np.isfinite(sample_vars) & (sample_vars > 0) & (residual_dfs > 0)
    if valid.sum() < 3:
        # Too few proteins to estimate the prior reliably.
        # Use the median observed variance as the prior and treat it as having
        # infinite prior df (complete pooling) so NaN-variance proteins still get a p-value.
        finite_pos = np.isfinite(sample_vars) & (sample_vars > 0)
        prior_var = (
            float(np.median(sample_vars[finite_pos])) if finite_pos.any() else 1.0
        )
        squeezed = np.where(finite_pos, sample_vars, prior_var)
        df_prior_fallback = np.inf if finite_pos.any() else 0.0
        return squeezed, df_prior_fallback

    sv = sample_vars[valid]
    df = residual_dfs[valid]

    # z_g = log(s²_g) − (ψ(d_g/2) − log(d_g/2))  →  E[z_g] ≈ log(s0²)
    z = np.log(sv) - (digamma(df / 2) - np.log(df / 2))
    z_mean = float(np.mean(z))
    s0_sq = np.exp(z_mean)

    # Var[z_g] ≈ trigamma(d0/2) + mean(trigamma(d_g/2))
    z_var = float(np.var(z, ddof=1))
    tg_correction = float(np.mean(polygamma(1, df / 2)))
    target_tg = z_var - tg_correction

    if target_tg <= 0:
        # Observed inter-protein spread ≤ expected sampling noise → prior df is
        # effectively infinite (complete pooling toward the grand mean variance).
        df_prior = np.inf
    else:
        df_prior = max(2.0 * _trigamma_inv(target_tg), 0.0)

    # Posterior: s̃²_g = (d0·s0² + d_g·s²_g) / (d0 + d_g)
    # Build element-by-element to avoid inf/inf arithmetic when df_prior is infinite.
    squeezed = np.full(len(sample_vars), s0_sq)
    valid_mask = np.isfinite(sample_vars) & (residual_dfs > 0)
    if np.isinf(df_prior):
        # Complete pooling: every protein gets the grand-mean prior variance
        pass  # squeezed already set to s0_sq everywhere
    else:
        dg = residual_dfs[valid_mask]
        squeezed[valid_mask] = (df_prior * s0_sq + dg * sample_vars[valid_mask]) / (
            df_prior + dg
        )
    return squeezed, df_prior


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
            n_proteins = len(expr)
            sample_vars = np.full(n_proteins, np.nan)
            residual_dfs = np.zeros(n_proteins)
            mean_diffs = np.full(n_proteins, np.nan)
            se_factors = np.full(n_proteins, np.nan)  # sqrt(1/nA + 1/nB)

            for idx in range(n_proteins):
                row = expr.iloc[idx]
                a = row[COND_A].dropna()
                b = row[COND_B].dropna()
                nA, nB = len(a), len(b)
                if nA < 1 or nB < 1:
                    continue
                mean_diffs[idx] = b.mean() - a.mean()
                se_factors[idx] = np.sqrt(1.0 / nA + 1.0 / nB)
                if nA >= 2 and nB >= 2:
                    pooled_var = (
                        (nA - 1) * a.var(ddof=1) + (nB - 1) * b.var(ddof=1)
                    ) / (nA + nB - 2)
                    sample_vars[idx] = pooled_var
                    residual_dfs[idx] = nA + nB - 2

            squeezed_vars, df_prior = _squeeze_var(sample_vars, residual_dfs)

            for idx in range(n_proteins):
                if not np.isfinite(mean_diffs[idx]) or not np.isfinite(se_factors[idx]):
                    continue
                sv = squeezed_vars[idx]
                if not np.isfinite(sv) or sv <= 0:
                    continue
                se = np.sqrt(sv) * se_factors[idx]
                if se == 0:
                    continue
                t_stat = mean_diffs[idx] / se
                df_total = df_prior + residual_dfs[idx]
                if df_total <= 0:
                    continue
                p_values[idx] = float(2 * t_dist.sf(abs(t_stat), df=df_total))

            success = True
            feedback = "✅ Limma moderated t-test applied. Variance estimates were squeezed toward a common prior, giving a fairer hearing to proteins measured with few replicates."

        elif test == "mannwhitneyu":
            # With only N_REP replicates per condition the exact Mann-Whitney U
            # test has extremely coarse p-value resolution and cannot reach p < 0.1
            # for n=3 vs n=3.  The asymptotic (normal approximation with continuity
            # correction) method is appropriate here and gives continuous p-values.
            for idx in range(len(expr)):
                row = expr.iloc[idx]
                a = row[COND_A].dropna()
                b = row[COND_B].dropna()

                if len(a) == 0 or len(b) == 0:
                    p_values[idx] = np.nan
                    continue

                try:
                    _, p = mannwhitneyu(
                        a, b, alternative="two-sided", method="asymptotic"
                    )
                    p_values[idx] = p
                except ValueError:
                    p_values[idx] = np.nan
            success = True
            feedback = "✅ Mann-Whitney U test applied. Samples were compared non-parametrically using the normal approximation, without assuming the data are normally distributed."

        elif test == "permutation":
            N_PERMUTATIONS = 1000
            rng = np.random.default_rng(42)
            n_a = len(COND_A)
            n_b = len(COND_B)
            n_total = n_a + n_b

            # Build a single (n_proteins × n_samples) matrix for all proteins at once.
            X = expr[COND_A + COND_B].values  # shape (n_proteins, n_total)

            # Observed statistic: mean(B) - mean(A) per protein, ignoring NaN.
            obs_stat = np.nanmean(X[:, n_a:], axis=1) - np.nanmean(X[:, :n_a], axis=1)

            # Global permutations: the same label shuffle is applied to every protein
            # simultaneously, preserving cross-protein correlation structure.
            # Accumulate all permuted statistics in a matrix for pooled null.
            null_matrix = np.empty((len(expr), N_PERMUTATIONS))
            for k in range(N_PERMUTATIONS):
                perm_idx = rng.permutation(n_total)
                X_perm = X[:, perm_idx]
                null_matrix[:, k] = np.nanmean(X_perm[:, n_a:], axis=1) - np.nanmean(
                    X_perm[:, :n_a], axis=1
                )

            # Variance-stabilisation (Perseus-style): divide each protein's observed
            # statistic and null statistics by that protein's permutation standard
            # deviation so that all proteins contribute on the same scale before
            # pooling across proteins.
            perm_std = np.nanstd(null_matrix, axis=1, ddof=1)
            valid = np.isfinite(obs_stat) & (perm_std > 0)
            obs_z = np.where(valid, obs_stat / perm_std, np.nan)
            null_z = null_matrix / perm_std[:, np.newaxis]

            # Pool all stabilised null statistics across proteins into one global null
            # distribution.  Using only valid proteins avoids NaN contamination.
            pooled_null_sorted = np.sort(np.abs(null_z[valid, :].ravel()))
            n_pooled = len(pooled_null_sorted)

            # Two-tailed p-value: fraction of pooled null >= |obs_z_i|.
            # Phipson-Smyth (2010): add 1 to numerator and denominator so p != 0.
            abs_obs_z = np.abs(np.where(valid, obs_z, 0.0))
            exceed = n_pooled - np.searchsorted(
                pooled_null_sorted, abs_obs_z, side="left"
            )
            p_values = np.where(valid, (exceed + 1) / (n_pooled + 1), np.nan)

            success = True
            n_valid = int(valid.sum())
            feedback = (
                f"✅ Permutation test applied ({N_PERMUTATIONS} global permutations, "
                f"{n_valid} proteins). Variance-stabilised statistics were pooled "
                f"across all proteins to build a shared null distribution "
                f"({n_valid * N_PERMUTATIONS:,} null values), following the Perseus approach."
            )

        elif test == "sam":
            # SAM (Significance Analysis of Microarrays; Tusher et al. 2001).
            # Computes a regularised fold-change statistic:
            #   d(i) = (mean_B − mean_A) / (s(i) + s₀)
            # where s(i) is the pooled standard error per protein and s₀ is a
            # small positive "fudge factor" (5th percentile of all s(i)) that
            # prevents spuriously significant calls for near-zero-variance proteins.
            # P-values are obtained by permuting sample labels while keeping the
            # denominator fixed at the observed s(i) + s₀, then pooling the
            # resulting null statistics across all proteins.
            N_PERMUTATIONS = 1000
            rng = np.random.default_rng(42)
            n_a = len(COND_A)
            n_b = len(COND_B)
            n_total = n_a + n_b
            n_prot = len(expr)
            X = expr[COND_A + COND_B].values.astype(float)  # (n_prot, n_total)

            # Per-protein pooled SE and observed mean difference
            se_obs = np.full(n_prot, np.nan)
            mean_diff_obs = np.full(n_prot, np.nan)
            valid = np.zeros(n_prot, dtype=bool)

            for idx in range(n_prot):
                a = X[idx, :n_a]
                b = X[idx, n_a:]
                a = a[np.isfinite(a)]
                b = b[np.isfinite(b)]
                na, nb = len(a), len(b)
                if na < 2 or nb < 2:
                    continue
                sp2 = ((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (
                    na + nb - 2
                )
                se_i = np.sqrt(sp2 * (1.0 / na + 1.0 / nb))
                if not np.isfinite(se_i):
                    continue
                mean_diff_obs[idx] = b.mean() - a.mean()
                se_obs[idx] = se_i
                valid[idx] = True

            # Fudge factor: 5th percentile of per-protein SEs
            se_valid_vals = se_obs[valid]
            s0 = (
                float(np.percentile(se_valid_vals, 5))
                if len(se_valid_vals) > 0
                else 0.0
            )

            # Observed SAM statistic; denominator is fixed for permutations too.
            # Clip to a minimum of 1e-12 so division is always safe (proteins with
            # zero SE and zero s0 get an effectively infinite SAM statistic, which
            # is correct — they are trivially significant if their means differ).
            denom = np.where(valid, np.fmax(se_obs + s0, 1e-12), 1.0)
            d_obs = np.where(valid, mean_diff_obs / denom, np.nan)

            # Null distribution: permute labels, reuse observed denominator
            null_matrix = np.empty((n_prot, N_PERMUTATIONS))
            null_matrix[:] = np.nan
            for perm_k in range(N_PERMUTATIONS):
                perm_idx = rng.permutation(n_total)
                X_perm = X[:, perm_idx]
                md_perm = np.nanmean(X_perm[:, n_a:], axis=1) - np.nanmean(
                    X_perm[:, :n_a], axis=1
                )
                null_matrix[:, perm_k] = np.where(valid, md_perm / denom, np.nan)

            # Pool |null d| across all valid proteins
            pooled_null_sorted = np.sort(np.abs(null_matrix[valid, :].ravel()))
            n_pooled = len(pooled_null_sorted)

            # Two-tailed p-value (Phipson & Smyth 2010 bias correction)
            abs_d_obs = np.abs(np.where(valid, d_obs, 0.0))
            exceed = n_pooled - np.searchsorted(
                pooled_null_sorted, abs_d_obs, side="left"
            )
            p_values = np.where(valid, (exceed + 1) / (n_pooled + 1), np.nan)

            n_valid = int(valid.sum())
            success = True
            feedback = (
                f"✅ SAM test applied ({N_PERMUTATIONS} permutations, {n_valid} proteins). "
                f"A regularised fold-change statistic (fudge factor s₀ = {s0:.4f}) "
                "was used to stabilise variance estimates and reduce false positives "
                "for low-variance proteins."
            )
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
        "data_review": _simulate_data_review,
        "filtering": _simulate_filtering,
        "transform": _simulate_transform,
        "normalize": _simulate_normalize,
        "imputer": _simulate_imputer,
        "multiple_testing_corrector": _simulate_multiple_testing_corrector,
        "the_cutter": _simulate_the_cutter,
        "statistical_analysis": _simulate_statistical_analysis,
        "final_report": _simulate_final_report,
        # ...
    }
)
# Additional station simulators can be added to the STATION_SIMULATORS dict following the same pattern.
# The key MUST correspond to the station_id used in the frontend configuration (frontend/src/assets/stations.json),
# and the value is a function that takes (dataset, params) and returns a dict with results.
