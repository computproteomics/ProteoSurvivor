import io
import base64
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

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

def boxplot(df, cols, title="Distribution Comparison"):
    """Generate a boxplot for the specified columns in the dataframe."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.boxplot(data=df[cols], ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Intensity")
    ax.set_xlabel("Columns")
    ax.tick_params(axis="x", rotation=30)

    return fig_to_base64(fig)


def adjusted_pvalue_histograms_by_species(df, value_col="p_adjusted", species_col="Organism", bins=30):
    """Create one adjusted p-value histogram per species and return base64-encoded images."""
    if df is None or value_col not in df.columns:
        return []

    numeric_values = pd.to_numeric(df[value_col], errors="coerce")
    valid_mask = numeric_values.notna() & np.isfinite(numeric_values)
    if not valid_mask.any():
        return []

    # If no species column, just return one histogram for all values
    if species_col not in df.columns:
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.histplot(numeric_values[valid_mask], bins=bins, ax=ax, color="#2563eb", edgecolor="white")
        ax.set_xlim(0, 1)
        ax.set_title("Adjusted p-value distribution")
        ax.set_xlabel("Adjusted p-value")
        ax.set_ylabel("Protein count")
        return [fig_to_base64(fig)]

    # If species column exists, create a histogram for each species
    work_df = df.loc[valid_mask, [species_col]].copy()
    work_df[value_col] = numeric_values[valid_mask]

    images = []
    grouped = work_df.assign(**{species_col: work_df[species_col].fillna("Unknown")}).groupby(species_col)
    for species, species_df in grouped:
        species_values = species_df[value_col]
        if species_values.empty:
            continue

        fig, ax = plt.subplots(figsize=(6, 4))
        sns.histplot(species_values, bins=bins, ax=ax, color="#16a34a", edgecolor="white")
        ax.set_xlim(0, 1)
        ax.set_title(f"Adjusted p-value distribution - {species}")
        ax.set_xlabel("Adjusted p-value")
        ax.set_ylabel("Protein count")
        images.append(fig_to_base64(fig))

    return images