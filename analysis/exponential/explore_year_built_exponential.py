# %%
"""Explore house construction year and sale price with an exponential trend.

Run in Jupyter from repository root:
    %run analysis/exponential/explore_year_built_exponential.py
Dependencies: %pip install pandas numpy matplotlib

Reads analysis/cleaning/AmesHousing-Cleaned.csv. Outputs stay in
analysis/exponential with the year_built_exponential prefix.
When pasting into Jupyter, use a working directory inside this repository.
The curve is fitted by least squares on log prices, not on dollar prices.
It describes fitted geometric mean prices; no arithmetic-mean correction
is applied. Year Built is the house construction year, not the lot's age.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


def fit_ols(features, target):
    """Fit centered predictors and return slopes and fitted target values."""
    centered = features - features.mean()
    design = np.column_stack([np.ones(len(features)), centered.to_numpy(dtype=float)])
    coefficients = np.linalg.lstsq(design, target.to_numpy(dtype=float), rcond=None)[0]
    return pd.Series(coefficients[1:], index=features.columns), design @ coefficients


def r_squared(actual, fitted):
    return 1 - np.sum((actual - fitted) ** 2) / np.sum((actual - np.mean(actual)) ** 2)


def explore_year_built_exponential(input_path=None):
    start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    analysis_dir = next(
        (root / "analysis" for root in (start, *start.parents)
         if (root / "analysis" / "cleaning").is_dir()),
        None,
    )
    if analysis_dir is None:
        raise FileNotFoundError("Run from within the repository containing analysis/cleaning.")
    base = analysis_dir / "exponential"
    source = Path(input_path) if input_path is not None else analysis_dir / "cleaning" / "AmesHousing-Cleaned.csv"
    data = pd.read_csv(source)
    numeric_controls = ["Year Built", "Gr Liv Area", "Overall Qual", "Overall Cond", "Lot Area"]
    required = numeric_controls + ["SalePrice", "Neighborhood", "Yr Sold"]
    working = data[required].copy()
    for column in numeric_controls + ["SalePrice", "Yr Sold"]:
        working[column] = pd.to_numeric(working[column], errors="coerce")
    working = working.dropna(subset=required)
    working = working.loc[working["SalePrice"] > 0].copy()
    if len(working) < 2 or working["Year Built"].nunique() < 2:
        raise ValueError("At least two construction years with valid positive prices are required.")

    prices = working["SalePrice"]
    log_prices = np.log(prices)
    simple_features = working[["Year Built"]]
    slopes, fitted_log = fit_ols(simple_features, log_prices)
    slope = slopes["Year Built"]
    reference_year = 1970
    reference_price = np.exp(log_prices.mean() + slope * (reference_year - working["Year Built"].mean()))
    fitted_prices = np.exp(fitted_log)

    categories = pd.get_dummies(
        working[["Neighborhood", "Yr Sold"]].astype("string"), drop_first=True, dtype=float
    )
    adjusted_features = pd.concat([working[numeric_controls], categories], axis=1)
    adjusted_slopes, adjusted_fitted_log = fit_ols(adjusted_features, log_prices)
    _, fitted_linear = fit_ols(simple_features, prices)

    # Dollar-scale R squared uses the back-transformed exponential predictions.
    # Log-scale R squared describes a different target and must be labeled separately.
    model_summary = pd.DataFrame([
        {"Model": "Exponential: construction year only",
         "Year coefficient": slope,
         "Percent difference per newer construction year": 100 * np.expm1(slope),
         "Percent difference per 10 newer construction years": 100 * np.expm1(10 * slope),
         "Log-price R squared": r_squared(log_prices, fitted_log),
         "Dollar-price R squared": r_squared(prices, fitted_prices)},
        {"Model": "Exponential: adjusted",
         "Year coefficient": adjusted_slopes["Year Built"],
         "Percent difference per newer construction year": 100 * np.expm1(adjusted_slopes["Year Built"]),
         "Percent difference per 10 newer construction years": 100 * np.expm1(10 * adjusted_slopes["Year Built"]),
         "Log-price R squared": r_squared(log_prices, adjusted_fitted_log),
         "Dollar-price R squared": r_squared(prices, np.exp(adjusted_fitted_log))},
    ])
    model_summary.to_csv(base / "year_built_exponential_model_summary.csv", index=False)

    working["Construction decade"] = (working["Year Built"] // 10 * 10).astype(int)
    decade_summary = working.groupby("Construction decade")["SalePrice"].agg(
        Sales="count", Mean="mean", Median="median",
        Geometric_mean=lambda values: np.exp(np.log(values).mean()),
    )
    decade_summary.to_csv(base / "year_built_exponential_decade_summary.csv")

    print(f"Analyzed {len(working):,} of {len(data):,} rows; sales from "
          f"{working['Yr Sold'].min():.0f} to {working['Yr Sold'].max():.0f}.")
    print(f"Exponential trend: Price = ${reference_price:,.2f} * "
          f"exp({slope:.8f} * (Year Built - {reference_year}))")
    print(f"Association per newer construction year: {100 * np.expm1(slope):.2f}%")
    print(f"Association per 10 newer construction years: {100 * np.expm1(10 * slope):.2f}%")
    print(f"Log-price R squared: {r_squared(log_prices, fitted_log):.4f}")
    print(f"Dollar-price R squared: {r_squared(prices, fitted_prices):.4f}")
    print(f"Earlier linear model, refitted on the same rows, dollar-price R squared: "
          f"{r_squared(prices, fitted_linear):.4f}")
    print(f"Adjusted association per 10 newer construction years: "
          f"{100 * np.expm1(10 * adjusted_slopes['Year Built']):.2f}%")
    print("Adjustment includes living area, overall quality, overall condition, lot area, "
          "neighborhood, and categorical sale year in a log-price model.")
    print("\nConstruction-decade summary (USD):")
    print(decade_summary.round(0).to_string())
    print("\nInterpretation: geometric mean prices, not arithmetic mean predictions. "
          "This is a constant percentage association with construction year across houses, "
          "not annual appreciation of an individual house or a causal effect. "
          "Prices are historical nominal dollars. Outliers, sparse early decades, "
          "omitted property features, and imputations in the cleaned data can affect results.")

    years = np.linspace(working["Year Built"].min(), working["Year Built"].max(), 400)
    trend = reference_price * np.exp(slope * (years - reference_year))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    for axis in axes:
        axis.scatter(working["Year Built"], prices, s=12, alpha=0.23,
                     color="#2166ac", edgecolors="none")
        axis.plot(years, trend, color="#b35806", linewidth=2.5,
                  label="Exponential trend (fit on log prices)")
        axis.set(xlabel="House construction year", ylabel="Sale price (USD)")
        axis.grid(axis="y", alpha=0.2)
        axis.legend(loc="upper left", fontsize=9)
    axes[0].set_title("Sale prices and fitted exponential curve")
    axes[1].set_yscale("log")
    axes[1].set_yticks([10000, 25000, 50000, 100000, 250000, 500000, 1000000])
    axes[1].set_ylim(prices.min() * 0.8, prices.max() * 1.15)
    axes[1].minorticks_off()
    axes[1].set_title(f"Same curve on a log price axis (log R² = {r_squared(log_prices, fitted_log):.3f})")
    for axis in axes:
        axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value / 1000:,.0f}k"))
    fig.suptitle(f"Ames housing: {100 * np.expm1(10 * slope):.1f}% higher fitted price per decade newer", fontsize=15)
    chart_path = base / "year_built_exponential_sale_price.png"
    fig.savefig(chart_path, dpi=180)
    print(f"\nSaved chart: {chart_path.resolve()}")
    # Save the chart in terminal sessions; display it in Jupyter or GUI sessions.
    if str(plt.get_backend()).lower() != "agg":
        plt.show()
    else:
        plt.close(fig)
    return working, decade_summary, model_summary


# %%
if __name__ == "__main__":
    analysis_data, decade_summary, model_summary = explore_year_built_exponential()
