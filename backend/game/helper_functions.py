import io
import base64
import os
import tempfile
from pathlib import Path

_mpl_config_dir = Path(tempfile.gettempdir()) / "matplotlib"
_mpl_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_mpl_config_dir))

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from .models import StationRun

ORGANISM = "Organism"
FC = "fold_change"


def get_visited_stations(user) -> set[str]:
    """Return unique station IDs the authenticated user has completed."""
    if not getattr(user, "is_authenticated", False):
        return set()

    return set(
        StationRun.objects.filter(player=user).values_list("station_id", flat=True)
    )


def fig_to_base64(fig):
    """
    Convert Matplotlib figure into a Base64-encoded PNG string which
    can be returned in JSON and displayed directly in frontend.
    """
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def tr_boxplot(df, cols, title="Distribution Comparison"):
    """Generate a boxplot for the specified columns in the dataframe."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.boxplot(data=df[cols], ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Intensity")
    ax.set_xlabel("Columns")
    ax.tick_params(axis="x", rotation=30)

    return fig_to_base64(fig)


def sp_scatterplot(
    x,
    y,
    x_col="Total spectral count",
    y_col="Intensity",
    color=None,
    title="Scatter Plot",
):
    """Generate a scatter plot for the specified columns in the dataframe."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.scatterplot(x=x, y=y, color=color, ax=ax)
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)

    return fig_to_base64(fig)


def _create_histogram(values, title, xlabel, ylabel, bins, color, xlim=(0, 1)):
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(values, bins=bins, ax=ax, color=color, edgecolor="white")
    ax.set_xlim(xlim)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig_to_base64(fig)


def mtc_histograms(df, value_col="p_adjusted", species_col="Organism"):
    """Create one adjusted p-value histogram per species and return base64-encoded images."""

    # If species column doesn't exist, create single histogram
    if species_col not in df.columns:
        return _create_histogram(
            df[value_col],
            "Adjusted p-value distribution",
            "Adjusted p-value",
            "Protein count",
            30,
            "#2563eb",
        )

    # Create histogram for each species
    imgs = []
    grouped = df.assign(**{species_col: df[species_col].fillna("Unknown")}).groupby(
        species_col
    )
    for species, species_df in grouped:
        species_values = species_df[value_col]
        if not species_values.empty:
            title = f"Adjusted p-value distribution - {species}"
            imgs.append(
                _create_histogram(
                    species_values,
                    title,
                    "Adjusted p-value",
                    "Protein count",
                    30,
                    "#16a34a",
                )
            )

    return imgs


def histogram_compare(
    before_df, after_df, cols, title_before="Before", title_after="After", bins=50
):
    # Flatten numeric values and drop NaN/inf
    before = before_df[cols].to_numpy(dtype=float).ravel()
    after = after_df[cols].to_numpy(dtype=float).ravel()
    before = before[np.isfinite(before)]
    after = after[np.isfinite(after)]

    if before.size == 0 or after.size == 0:
        return []

    # Shared x-range and shared bins
    x_min = float(min(before.min(), after.min()))
    x_max = float(max(before.max(), after.max()))
    if x_min == x_max:
        x_max = x_min + 1.0

    bin_edges = np.linspace(x_min, x_max, bins + 1)

    images = []

    fig1, ax1 = plt.subplots(figsize=(6, 5))
    ax1.hist(before, bins=bin_edges, alpha=0.8, color="#1f77b4")
    ax1.set_title(title_before)
    ax1.set_xlabel("Intensity")
    ax1.set_ylabel("Count")
    ax1.set_xlim(x_min, x_max)
    images.append(fig_to_base64(fig1))

    fig2, ax2 = plt.subplots(figsize=(6, 5))
    ax2.hist(after, bins=bin_edges, alpha=0.8, color="#ff7f0e")
    ax2.set_title(title_after)
    ax2.set_xlabel("Intensity")
    ax2.set_ylabel("Count")
    ax2.set_xlim(x_min, x_max)
    images.append(fig_to_base64(fig2))

    return images


def plot_significant_proteins(df):
    """Generate a bar plot showing the number of significant proteins by organism."""
    positive_counts = df[df[FC] > 0].groupby(ORGANISM).size()
    negative_counts = df[df[FC] < 0].groupby(ORGANISM).size()

    organisms = sorted(set(positive_counts.index).union(negative_counts.index))
    positive_values = [int(positive_counts.get(org, 0)) for org in organisms]
    negative_values = [-int(negative_counts.get(org, 0)) for org in organisms]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(organisms, positive_values, color="#2ca02c", label="FC > 0")
    ax.bar(organisms, negative_values, color="#d62728", label="FC < 0")

    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Significant Proteins by Organism")
    ax.set_xlabel(ORGANISM)
    ax.set_ylabel("Protein Count")
    ax.tick_params(axis="x", rotation=30)
    ax.legend()

    return fig_to_base64(fig)


def imputer_before_after_stripgrid(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    cond_a_cols: list[str],
    cond_b_cols: list[str],
    title: str = "Before vs After Imputation by Sample",
    max_points_per_stage: int = 1200,
    random_state: int = 42,
):
    """Create a 2x3 stripplot grid comparing values before vs after imputation."""
    sample_cols = cond_a_cols + cond_b_cols
    if len(sample_cols) != 6:
        raise ValueError(
            "Expected exactly 6 sample columns (3 for condition A and 3 for condition B)."
        )

    fig, axes = plt.subplots(2, 3, figsize=(16, 10), sharey=True)
    axes = axes.flatten()

    palette = {"Before": "#0B3C8A", "After": "#FF1493"}

    for idx, sample_col in enumerate(sample_cols):
        ax = axes[idx]

        before_vals = pd.to_numeric(before_df[sample_col], errors="coerce").dropna()
        after_vals = pd.to_numeric(after_df[sample_col], errors="coerce").dropna()

        if len(before_vals) > max_points_per_stage:
            before_vals = before_vals.sample(
                n=max_points_per_stage, random_state=random_state
            )
        if len(after_vals) > max_points_per_stage:
            after_vals = after_vals.sample(
                n=max_points_per_stage, random_state=random_state
            )

        plot_df = pd.DataFrame(
            {
                "stage": ["Before"] * len(before_vals) + ["After"] * len(after_vals),
                "value": pd.concat([before_vals, after_vals], ignore_index=True),
            }
        )

        sns.stripplot(
            data=plot_df,
            x="stage",
            y="value",
            hue="stage",
            order=["Before", "After"],
            hue_order=["Before", "After"],
            palette=palette,
            jitter=0.25,
            dodge=False,
            size=2,
            alpha=0.7,
            ax=ax,
        )
        if ax.get_legend() is not None:
            ax.get_legend().remove()

        condition_label = "Condition A" if idx < 3 else "Condition B"
        ax.set_title(f"{condition_label} - {sample_col}")
        ax.set_xlabel("")
        ax.set_ylabel("Intensity" if idx % 3 == 0 else "")

    fig.suptitle(title, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig_to_base64(fig)


def plot_scores(true_positives=None, false_positives=None, min_fdr=1e-3):
    """Generate a scatter plot of all players' final-station results."""
    from .models import FinalStationResult

    def _fdr(tp, fp, min_fdr=1e-3):
        total = tp + fp
        if total <= 0:
            return None
        if fp > 0:
            return fp / total
        elif min_fdr is not None:
            return min_fdr
        else:
            return None

    results = FinalStationResult.objects.all().values_list(
        "true_positives", "false_positives"
    )

    x_values = []
    y_values = []
    for tp, fp in results:
        x_val = _fdr(tp, fp, min_fdr)
        if x_val is None:
            continue
        x_values.append(x_val)
        y_values.append(tp)

    current_x = None
    if true_positives is not None and false_positives is not None:
        current_x = _fdr(true_positives, false_positives, min_fdr)

    fig, ax = plt.subplots(figsize=(7, 5))
    if x_values:
        sns.scatterplot(
            x=x_values,
            y=y_values,
            ax=ax,
            color="#94a3b8",
            s=55,
            edgecolor="none",
            label=(
                "Others' results" if current_x is not None else "Final Station Results"
            ),
        )
    if current_x is not None and true_positives is not None:
        sns.scatterplot(
            x=[current_x],
            y=[true_positives],
            ax=ax,
            color="#ef4444",
            s=170,
            edgecolor="black",
            linewidth=0.8,
            label="Your result",
        )

    ax.set_title("Final Station Scores")
    ax.set_xlabel("FDR")
    ax.set_ylabel("True Positives")
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.grid(alpha=0.25)
    if ax.get_legend_handles_labels()[0]:
        ax.legend()

    return fig_to_base64(fig)


def filtering_piechart(num_before, num_after):
    """Generate a pie chart showing proteins retained vs removed during filtering."""
    removed = num_before - num_after
    sizes = [num_after, removed]
    labels = [f"Retained\n({num_after})", f"Removed\n({removed})"]
    colors = ["#2ca02c", "#d62728"]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    ax.set_title("Proteins: Retained vs Removed")

    return fig_to_base64(fig)


def filtering_scatterplot(df, relevant_cols=None):
    """
    Generate a scatter plot comparing Condition A vs Condition B protein abundances.
    This helps visualize whether filtering reduces spread around the diagonal.
    """
    if df is None or df.empty:
        return None

    if relevant_cols is None:
        relevant_cols = [
            col
            for col in df.columns
            if col.startswith("ConditionA_Sample")
            or col.startswith("ConditionB_Sample")
        ]

    cond_a_cols = [col for col in relevant_cols if col.startswith("ConditionA_Sample")]
    cond_b_cols = [col for col in relevant_cols if col.startswith("ConditionB_Sample")]

    if not cond_a_cols or not cond_b_cols:
        return None

    values = df[cond_a_cols + cond_b_cols].replace([np.inf, -np.inf], np.nan)
    cond_a_mean = values[cond_a_cols].mean(axis=1)
    cond_b_mean = values[cond_b_cols].mean(axis=1)

    plot_df = pd.DataFrame(
        {"Condition A": cond_a_mean, "Condition B": cond_b_mean}
    ).dropna()
    if plot_df.empty:
        return None

    x_min = float(min(plot_df["Condition A"].min(), plot_df["Condition B"].min()))
    x_max = float(max(plot_df["Condition A"].max(), plot_df["Condition B"].max()))
    if x_min == x_max:
        x_max = x_min + 1.0

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(
        data=plot_df,
        x="Condition A",
        y="Condition B",
        alpha=0.65,
        s=45,
        ax=ax,
        color="#2563eb",
    )
    ax.plot(
        [x_min, x_max], [x_min, x_max], linestyle="--", color="#6b7280", linewidth=1.2
    )
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(x_min, x_max)
    ax.set_xlabel("Condition A mean intensity")
    ax.set_ylabel("Condition B mean intensity")
    ax.set_title("Condition A vs Condition B")
    ax.grid(True, alpha=0.25)

    return fig_to_base64(fig)


def volcano_plot(
    df, title, p_val_col, sig_threshold=None, fc_threshold=None, fc_col="FC"
):
    """Generate a volcano plot for the given dataframe.

    Returns a base64 image string, or None when required inputs are invalid/empty.
    """
    if p_val_col not in df.columns or fc_col not in df.columns:
        return None

    plot_df = df[[fc_col, p_val_col]].copy()
    plot_df[fc_col] = pd.to_numeric(plot_df[fc_col], errors="coerce")
    plot_df[p_val_col] = pd.to_numeric(plot_df[p_val_col], errors="coerce")
    plot_df = plot_df.replace([np.inf, -np.inf], np.nan).dropna(
        subset=[fc_col, p_val_col]
    )
    plot_df = plot_df[plot_df[p_val_col] > 0]
    if plot_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(7, 5))
    plot_df["neg_log10_p"] = -np.log10(plot_df[p_val_col])

    if sig_threshold is None or fc_threshold is None:
        sns.scatterplot(
            data=plot_df,
            x=fc_col,
            y="neg_log10_p",
            ax=ax,
            color="grey",
            edgecolor="none",
        )
    else:
        # Classify significance based on thresholds
        plot_df["significant"] = "not_sig"
        plot_df.loc[
            (plot_df[p_val_col] < sig_threshold) & (plot_df[fc_col] >= fc_threshold),
            "significant",
        ] = "up"
        plot_df.loc[
            (plot_df[p_val_col] < sig_threshold) & (plot_df[fc_col] <= -fc_threshold),
            "significant",
        ] = "down"

        sns.scatterplot(
            data=plot_df,
            x=fc_col,
            y="neg_log10_p",
            hue="significant",
            hue_order=["up", "down", "not_sig"],
            palette={"up": "red", "down": "blue", "not_sig": "grey"},
            ax=ax,
            edgecolor="none",
        )
        ax.axhline(-np.log10(sig_threshold), color="red", linestyle="--", linewidth=1)
        ax.axvline(-fc_threshold, color="red", linestyle="--", linewidth=1)
        ax.axvline(fc_threshold, color="red", linestyle="--", linewidth=1)

    ax.set_title(title)
    ax.set_xlabel("log2 fold change")
    ax.set_ylabel("-log10(p-value)")
    return fig_to_base64(fig)
