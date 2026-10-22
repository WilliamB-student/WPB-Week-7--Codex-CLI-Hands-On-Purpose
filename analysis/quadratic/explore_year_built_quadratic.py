# %%
"""Quadratic analysis of house construction year and sale price.

Jupyter: %run explore_year_built_quadratic.py
Dependencies: %pip install pandas numpy matplotlib
Reads AmesHousing-Cleaned.csv; all outputs use year_built_quadratic names.
Earlier analysis files are preserved. Fits dollar prices by least squares.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


REFERENCE_YEAR = 1970


def fit_ols(features, target):
    design = np.column_stack([np.ones(len(features)), features.to_numpy(dtype=float)])
    coefficients = np.linalg.lstsq(design, target.to_numpy(dtype=float), rcond=None)[0]
    return pd.Series(coefficients, index=["Intercept", *features.columns]), design @ coefficients


def r_squared(actual, fitted):
    return 1 - np.sum((actual - fitted) ** 2) / np.sum((actual - np.mean(actual)) ** 2)


def decade_difference(coefficients, year):
    """Predicted price at year+10 minus price at year, holding controls fixed."""
    t = year - REFERENCE_YEAR
    return 10 * coefficients["Year offset"] + coefficients["Year offset squared"] * (20 * t + 100)


def explore_year_built_quadratic(input_path=None):
    base = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    source = Path(input_path) if input_path is not None else base / "AmesHousing-Cleaned.csv"
    data = pd.read_csv(source)
    controls = ["Gr Liv Area", "Overall Qual", "Overall Cond", "Lot Area"]
    required = ["Year Built", "SalePrice", "Neighborhood", "Yr Sold", *controls]
    working = data[required].copy()
    for column in ["Year Built", "SalePrice", "Yr Sold", *controls]:
        working[column] = pd.to_numeric(working[column], errors="coerce")
    working = working.replace([np.inf, -np.inf], np.nan).dropna(subset=required)
    working = working.loc[working["SalePrice"] > 0].copy()
    if working["Year Built"].nunique() < 3:
        raise ValueError("A quadratic model requires at least three distinct construction years.")

    prices = working["SalePrice"]
    offset = working["Year Built"] - REFERENCE_YEAR
    features = pd.DataFrame({"Year offset": offset, "Year offset squared": offset ** 2})
    quadratic, fitted = fit_ols(features, prices)
    linear, fitted_linear = fit_ols(features[["Year offset"]], prices)
    exponential, fitted_log = fit_ols(features[["Year offset"]], np.log(prices))
    categories = pd.get_dummies(
        working[["Neighborhood", "Yr Sold"]].astype("string"), drop_first=True, dtype=float
    )
    centered_controls = working[controls] - working[controls].mean()
    adjusted_features = pd.concat([features, centered_controls, categories], axis=1)
    adjusted, fitted_adjusted = fit_ols(adjusted_features, prices)

    comparison = pd.DataFrame([
        {"Model": name, "Rows": len(working), "Dollar-price R squared": r_squared(prices, prediction),
         "Dollar-price RMSE": np.sqrt(np.mean((prices - prediction) ** 2)),
         "Fit target": target}
        for name, prediction, target in [
            ("Linear: year only", fitted_linear, "SalePrice"),
            ("Exponential: year only", np.exp(fitted_log), "log(SalePrice)"),
            ("Quadratic: year only", fitted, "SalePrice"),
            ("Quadratic: adjusted", fitted_adjusted, "SalePrice"),
        ]
    ])
    comparison.to_csv(source.with_name("year_built_quadratic_model_summary.csv"), index=False)
    pd.concat([quadratic.rename("Quadratic: year only"), adjusted.rename("Quadratic: adjusted")],
              axis=1).rename_axis("Term").to_csv(source.with_name("year_built_quadratic_coefficients.csv"))

    starting_years = [year for year in [1900, 1930, 1950, 1970, 1990, 2000]
                      if working["Year Built"].min() <= year <= working["Year Built"].max() - 10]
    contrasts = pd.DataFrame({
        "Construction year": starting_years,
        "Comparison construction year": [year + 10 for year in starting_years],
        "Unadjusted price difference USD": [decade_difference(quadratic, year) for year in starting_years],
        "Adjusted price difference USD": [decade_difference(adjusted, year) for year in starting_years],
    })
    contrasts.to_csv(source.with_name("year_built_quadratic_decade_differences.csv"), index=False)
    working["Construction decade"] = (working["Year Built"] // 10 * 10).astype(int)
    working["Quadratic fitted price"] = fitted
    decade_summary = working.groupby("Construction decade").agg(
        Sales=("SalePrice", "count"), Mean=("SalePrice", "mean"), Median=("SalePrice", "median"),
        Mean_quadratic_fitted_price=("Quadratic fitted price", "mean"),
    )
    decade_summary.to_csv(source.with_name("year_built_quadratic_decade_summary.csv"))

    print(f"Analyzed {len(working):,} of {len(data):,} sales from "
          f"{working['Yr Sold'].min():.0f} to {working['Yr Sold'].max():.0f}.")
    print(f"Construction years: {working['Year Built'].min():.0f}-{working['Year Built'].max():.0f}.")
    print(f"Quadratic: Price = {quadratic['Intercept']:,.2f} "
          f"+ ({quadratic['Year offset']:,.4f})*t "
          f"+ ({quadratic['Year offset squared']:,.6f})*t^2; t = Year Built - {REFERENCE_YEAR}.")
    if quadratic["Year offset squared"] != 0:
        vertex = REFERENCE_YEAR - quadratic["Year offset"] / (2 * quadratic["Year offset squared"])
        print(f"Fitted curve turning point: construction year {vertex:.1f}.")
    print("\nModel comparison (in-sample, same rows and dollar-price scale):")
    print(comparison.round(4).to_string(index=False))
    print("\nPredicted differences for construction 10 years later:")
    print(contrasts.round(0).to_string(index=False))
    print("\nAdjusted model includes both construction-year terms, living area, quality, "
          "condition, lot area, neighborhood, and categorical sale year. Other numeric "
          "controls are centered at sample means; categorical baselines are omitted dummy levels.")
    print("Associations are not causal effects or house appreciation over time. "
          "Prices are historical nominal dollars. Sparse older years, outliers, omitted "
          "features, and prior imputations affect results. Avoid extrapolating the parabola "
          "outside observed years. Fit comparisons describe this sample, not predictive validation. "
          "The adjusted model's R squared includes all controls.")

    years = np.linspace(working["Year Built"].min(), working["Year Built"].max(), 400)
    t = years - REFERENCE_YEAR
    trend = quadratic["Intercept"] + quadratic["Year offset"] * t + quadratic["Year offset squared"] * t ** 2
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    axes[0].scatter(working["Year Built"], prices, s=12, alpha=0.23,
                    color="#2166ac", edgecolors="none")
    axes[0].plot(years, trend, color="#b35806", linewidth=2.5, label="Quadratic trend")
    axes[0].set(xlabel="House construction year", ylabel="Sale price (USD)",
                title=f"Quadratic construction-year model (R² = {r_squared(prices, fitted):.3f})")
    contrast_years = np.linspace(years.min(), years.max() - 10, 400)
    axes[1].plot(contrast_years, decade_difference(quadratic, contrast_years),
                 color="#b35806", linewidth=2.5, label="Construction year only")
    axes[1].plot(contrast_years, decade_difference(adjusted, contrast_years),
                 color="#2166ac", linewidth=2.5, label="Adjusted for property features")
    axes[1].axhline(0, color="gray", linestyle="--", linewidth=1)
    axes[1].set(xlabel="Starting construction year (compared with 10 years later)",
                ylabel="Predicted price difference (USD)", title="The price difference varies by construction year")
    for axis in axes:
        axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value / 1000:,.0f}k"))
        axis.grid(axis="y", alpha=0.2)
        axis.legend(fontsize=9)
    fig.suptitle("Ames housing: quadratic relationship between construction year and sale price", fontsize=14)
    chart_path = source.with_name("year_built_quadratic_sale_price.png")
    fig.savefig(chart_path, dpi=180)
    print(f"\nSaved chart: {chart_path.resolve()}")
    if str(plt.get_backend()).lower() != "agg":
        plt.show()
    else:
        plt.close(fig)
    return working, decade_summary, comparison, contrasts, quadratic, adjusted


# %%
if __name__ == "__main__":
    analysis_data, decade_summary, model_summary, decade_differences, quadratic_coefficients, adjusted_coefficients = explore_year_built_quadratic()
