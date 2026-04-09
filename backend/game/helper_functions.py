import io
import base64
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def fig_to_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def create_two_transformation_plots(df, intensity_cols):

    # Plot 2: boxplot
    fig2, ax2 = plt.subplots(figsize=(6, 5))
    sns.boxplot(data=[raw_values, log_values], ax=ax2)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Before log2", "After log2"])
    ax2.set_title("Distribution Comparison")
    ax2.set_ylabel("Intensity")

    return {
        "transformed_df": df_log2,
        "plots": [
            {
                "id": "distribution_plot",
                "title": "Before and After Log2 Transformation",
                "image_base64": fig_to_base64(fig1),
            },
        ],
    }