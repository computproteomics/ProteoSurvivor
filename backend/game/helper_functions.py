import io
import base64
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

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
        return _create_histogram(df[value_col], "Adjusted p-value distribution", "Adjusted p-value", "Protein count", 30, "#2563eb")
    
    # Create histogram for each species
    imgs = []
    grouped = df.assign(**{species_col: df[species_col].fillna("Unknown")}).groupby(species_col)
    for species, species_df in grouped:
        species_values = species_df[value_col]
        if not species_values.empty:
            title = f"Adjusted p-value distribution - {species}"
            imgs.append(_create_histogram(species_values, title, "Adjusted p-value", "Protein count", 30, "#16a34a"))

    return imgs


def imputer_before_after_swarmgrid(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    cond_a_cols: list[str],
    cond_b_cols: list[str],
    title: str = "Before vs After Imputation by Sample",
):
    """Create a 2x3 swarmplot grid comparing values before vs after imputation."""
    sample_cols = cond_a_cols + cond_b_cols
    if len(sample_cols) != 6:
        raise ValueError("Expected exactly 6 sample columns (3 for condition A and 3 for condition B).")

    fig, axes = plt.subplots(2, 3, figsize=(16, 10), sharey=True)
    axes = axes.flatten()

    palette = {"Before": "#0B3C8A", "After": "#FF1493"}

    for idx, sample_col in enumerate(sample_cols):
        ax = axes[idx]

        before_vals = pd.to_numeric(before_df[sample_col], errors="coerce")
        after_vals = pd.to_numeric(after_df[sample_col], errors="coerce")

        plot_df = pd.DataFrame(
            {
                "stage": ["Before"] * len(before_vals) + ["After"] * len(after_vals),
                "value": pd.concat([before_vals, after_vals], ignore_index=True),
            }
        ).dropna(subset=["value"])

        sns.swarmplot(
            data=plot_df,
            x="stage",
            y="value",
            order=["Before", "After"],
            palette=palette,
            size=2,
            alpha=0.75,
            ax=ax,
        )

        condition_label = "Condition A" if idx < 3 else "Condition B"
        ax.set_title(f"{condition_label} - {sample_col}")
        ax.set_xlabel("")

        if idx % 3 == 0:
            ax.set_ylabel("Intensity")
        else:
            ax.set_ylabel("")

    fig.suptitle(title, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig_to_base64(fig)