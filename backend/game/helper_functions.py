import io
import base64
import math
import matplotlib
matplotlib.use("Agg")
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

ORGANISM = "Organism"
FC = "fold_change"


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
    """ Create one adjusted p-value histogram per species and return base64-encoded images."""

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

def histogram_compare(before_df, after_df, cols, title_before="Before", title_after="After", bins=50):
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


def plot_scores(df, true_positives, false_positives):
    """Generate a scatter plot of all the player's results."""
    from .models import FinalStationResult

    def _score_x_axis(tp, fp):
        if tp <= 0:
            return None
        ratio = fp / tp
        ratio = max(ratio, 1e-12)
        return -math.log10(ratio)

    results = FinalStationResult.objects.all().values_list("true_positives", "false_positives")

    x_values = []
    y_values = []
    for tp, fp in results:
        x_val = _score_x_axis(tp, fp)
        if x_val is None:
            continue
        x_values.append(x_val)
        y_values.append(tp)

    current_x = _score_x_axis(true_positives, false_positives)

    fig, ax = plt.subplots(figsize=(7, 5))
    if x_values:
        sns.scatterplot(x=x_values, y=y_values, ax=ax, color="#94a3b8", s=55, edgecolor="none", label="Others' results")

    if current_x is not None:
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
    ax.set_xlabel("-log10(False Positive Rate)")
    ax.set_ylabel("True Positives")
    ax.grid(alpha=0.25)
    if ax.get_legend_handles_labels()[0]:
        ax.legend()

    return fig_to_base64(fig)
