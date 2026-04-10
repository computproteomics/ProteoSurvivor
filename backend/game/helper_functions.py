import io
import base64
import seaborn as sns
import matplotlib.pyplot as plt

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


def boxplot(df, cols, title="Distribution Comparison"):
    """Generate a boxplot for the specified columns in the dataframe."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.boxplot(data=df[cols], ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Intensity")
    ax.set_xlabel("Columns")
    ax.tick_params(axis="x", rotation=30)

    return fig_to_base64(fig)


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