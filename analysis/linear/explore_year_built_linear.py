# %%
"""Explore construction year and sale price in AmesHousing-Cleaned.csv.

Jupyter usage: %run explore_year_built.py
Dependencies: %pip install pandas numpy matplotlib
Outputs: year_built_sale_price.png and year_built_decade_summary.csv.
Year Built describes the house's construction, not when its lot was created.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


def fit_linear(features, target):
    """OLS with centered predictors; return coefficients and in-sample R squared."""
    centered = features - features.mean()
    design = np.column_stack([np.ones(len(features)), centered.to_numpy(dtype=float)])
    coefficients = np.linalg.lstsq(design, target.to_numpy(dtype=float), rcond=None)[0]
    predicted = design @ coefficients
    r_squared = 1 - np.sum((target - predicted) ** 2) / np.sum((target - target.mean()) ** 2)
    return pd.Series(coefficients[1:], index=features.columns), r_squared


def explore_year_built(input_path=None):
    base = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    source = Path(input_path) if input_path is not None else base / "AmesHousing-Cleaned.csv"
    data = pd.read_csv(source)
    numeric_controls = ["Year Built", "Gr Liv Area", "Overall Qual", "Overall Cond", "Lot Area"]
    required = numeric_controls + ["SalePrice", "Neighborhood", "Yr Sold"]
    working = data[required].copy()
    for column in numeric_controls + ["SalePrice", "Yr Sold"]:
        working[column] = pd.to_numeric(working[column], errors="coerce")
    working = working.dropna(subset=required)
    working = working.loc[working["SalePrice"] > 0].copy()
    if len(working) < 2 or working["Year Built"].nunique() < 2:
        raise ValueError("At least two construction years with valid sales are required.")

    working["Construction decade"] = (working["Year Built"] // 10 * 10).astype(int)
    decade_summary = working.groupby("Construction decade")["SalePrice"].agg(
        Sales="count", Mean="mean", Median="median",
        Q1=lambda values: values.quantile(0.25),
        Q3=lambda values: values.quantile(0.75),
    )
    decade_summary.to_csv(source.with_name("year_built_decade_summary.csv"))

    simple_coefficients, simple_r2 = fit_linear(working[["Year Built"]], working["SalePrice"])
    categories = pd.get_dummies(
        working[["Neighborhood", "Yr Sold"]].astype("string"), drop_first=True, dtype=float
    )
    adjusted_features = pd.concat([working[numeric_controls], categories], axis=1)
    adjusted_coefficients, _ = fit_linear(adjusted_features, working["SalePrice"])
    correlation = working["Year Built"].corr(working["SalePrice"])

    print(f"Analyzed {len(working):,} of {len(data):,} rows; sales from "
          f"{working['Yr Sold'].min():.0f} to {working['Yr Sold'].max():.0f}.")
    print(f"Pearson correlation: {correlation:.3f}")
    print(f"Unadjusted price difference per 10 newer construction years: "
          f"${10 * simple_coefficients['Year Built']:,.0f}")
    print(f"Variation explained by construction year alone (R squared): {simple_r2:.1%}")
    print(f"Adjusted price difference per 10 newer construction years: "
          f"${10 * adjusted_coefficients['Year Built']:,.0f}")
    print("Adjusted for living area, overall quality, overall condition, lot area, "
          "neighborhood, and sale year using an additive linear model.")
    print("\nPrices by construction decade (USD):")
    print(decade_summary.round(0).to_string())
    print("\nThese are associations, not causal effects. Renovations, sale conditions, "
          "and other omitted features can affect prices. Prices are historical nominal "
          "dollars. Sparse decades and unusual properties need care; all valid sales "
          "are retained. Results also inherit imputations from the cleaned CSV.")

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    axes[0].scatter(working["Year Built"], working["SalePrice"],
                    s=12, alpha=0.25, color="#2166ac", edgecolors="none")
    years = np.array([working["Year Built"].min(), working["Year Built"].max()])
    fitted = working["SalePrice"].mean() + simple_coefficients["Year Built"] * (
        years - working["Year Built"].mean()
    )
    axes[0].plot(years, fitted, color="#b35806", linewidth=2, label="Linear trend")
    axes[0].set(xlabel="House construction year", ylabel="Sale price (USD)",
                title=f"Newer houses tend to sell for more (r = {correlation:.2f})")
    axes[0].legend()

    positions = np.arange(len(decade_summary))
    axes[1].vlines(positions, decade_summary["Q1"], decade_summary["Q3"],
                   color="#2166ac", linewidth=5, alpha=0.5, label="Middle 50% of prices")
    axes[1].scatter(positions, decade_summary["Median"], color="#b35806", zorder=3,
                    label="Median price")
    axes[1].set_xticks(positions, [f"{decade}s\nn={count}" for decade, count in
                                  zip(decade_summary.index, decade_summary["Sales"])],
                       rotation=60, ha="right", fontsize=8)
    axes[1].set(xlabel="Construction decade and number of sales", ylabel="Sale price (USD)",
                title="Median price and price spread by construction decade")
    axes[1].legend()
    for axis in axes:
        axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value / 1000:,.0f}k"))
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("Ames housing: construction year and historical sale price", fontsize=15)
    chart_path = source.with_name("year_built_sale_price.png")
    fig.savefig(chart_path, dpi=180)
    print(f"\nSaved chart: {chart_path.resolve()}")
    plt.show()
    return working, decade_summary, simple_coefficients, adjusted_coefficients


# %%
if __name__ == "__main__":
    analysis_data, decade_summary, simple_coefficients, adjusted_coefficients = explore_year_built()
