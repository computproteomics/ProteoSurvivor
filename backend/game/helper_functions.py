import io
import base64
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
