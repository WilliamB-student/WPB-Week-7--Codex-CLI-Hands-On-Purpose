# %%
"""Clean AmesHousing-1.csv and write AmesHousing-Cleaned.csv.

In Jupyter Notebook, run this file from the repository root with:
    %run analysis/cleaning/clean_ames_housing.py

The cleaned DataFrame will be available as ``cleaned_data``. Install pandas
first if needed by running ``%pip install pandas`` in a notebook cell.
You can also paste this file into a notebook cell or run it with Python.
When pasting, use a working directory inside this repository. Paths are
resolved relative to its analysis folder; output goes in analysis/cleaning.
"""

from pathlib import Path

import pandas as pd


def clean_ames_housing(input_path=None, output_path=None):
    """Return the cleaned DataFrame and export it without a CSV row index.

    Missing numeric values use column medians, with neighborhood medians
    preferred for Lot Frontage. Missing categories use the most common value.
    Documented optional features use 'None' when absent; ambiguous missing
    feature descriptions use 'Unknown'. No outliers or columns are dropped.
    """
    start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    analysis_dir = next(
        (root / "analysis" for root in (start, *start.parents)
         if (root / "analysis" / "cleaning").is_dir()),
        None,
    )
    if analysis_dir is None:
        raise FileNotFoundError("Run from within the repository containing analysis/cleaning.")
    source = (
        Path(input_path) if input_path is not None
        else analysis_dir / "initial data" / "AmesHousing-1.csv"
    )
    destination = (
        Path(output_path) if output_path is not None
        else analysis_dir / "cleaning" / "AmesHousing-Cleaned.csv"
    )
    if source.resolve() == destination.resolve():
        raise ValueError("The output path must differ from the original dataset path.")

    # Preserve leading zeros and treat MS SubClass as a category, not a measure.
    # Preserve the literal category 'None', which pandas otherwise treats as NA.
    data = pd.read_csv(
        source,
        dtype={"PID": "string", "MS SubClass": "string"},
        keep_default_na=False,
        na_values=["", "NA", "N/A", "NaN", "nan", "NULL", "null"],
    )
    original_rows = len(data)
    data.columns = data.columns.str.strip()
    if data.columns.duplicated().any():
        raise ValueError("Column names must be unique after removing whitespace.")

    text_columns = data.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA)

    # Compare property records without the source file's row numbering.
    record_columns = [column for column in data.columns if column != "Order"]
    data = data.drop_duplicates(subset=record_columns).copy()
    duplicate_rows = original_rows - len(data)

    # A missing target cannot be reliably reconstructed for a housing dataset.
    data["SalePrice"] = pd.to_numeric(data["SalePrice"], errors="coerce")
    valid_price = data["SalePrice"].notna() & (data["SalePrice"] > 0)
    invalid_prices = int((~valid_price).sum())
    data = data.loc[valid_price].copy()
    if data.empty:
        raise ValueError("No records with a valid, positive SalePrice remain.")

    # NA in these optional categories explicitly means the feature is absent.
    for column in ["Alley", "Fence", "Misc Feature"]:
        data[column] = data[column].fillna("None")

    feature_groups = [
        ("Total Bsmt SF", ["Bsmt Qual", "Bsmt Cond", "Bsmt Exposure",
                           "BsmtFin Type 1", "BsmtFin Type 2"],
         ["BsmtFin SF 1", "BsmtFin SF 2", "Bsmt Unf SF", "Bsmt Full Bath", "Bsmt Half Bath"]),
        ("Garage Cars", ["Garage Type", "Garage Finish", "Garage Qual", "Garage Cond"],
         ["Garage Area", "Garage Yr Blt"]),
        ("Fireplaces", ["Fireplace Qu"], []),
        ("Pool Area", ["Pool QC"], []),
        ("Mas Vnr Area", ["Mas Vnr Type"], []),
    ]
    for size_column, descriptions, measurements in feature_groups:
        absent = data[size_column].eq(0)
        for column in descriptions:
            data.loc[absent & data[column].isna(), column] = "None"
            data[column] = data[column].fillna("Unknown")
        for column in measurements:
            # Zero years denote no garage; they are not estimated construction dates.
            data.loc[absent & data[column].isna(), column] = 0

    neighborhood_frontage = data.groupby("Neighborhood")["Lot Frontage"].transform("median")
    data["Lot Frontage"] = data["Lot Frontage"].fillna(neighborhood_frontage)

    # Fill remaining missing measurements and categories consistently.
    for column in data.columns:
        if pd.api.types.is_numeric_dtype(data[column]):
            median = data[column].median()
            if pd.isna(median):
                raise ValueError(f"Cannot estimate entirely missing numeric column: {column}")
            data[column] = data[column].fillna(median)
        else:
            if column in ["PID", "MS SubClass"]:
                data[column] = data[column].fillna("Unknown")
            else:
                modes = data[column].mode()
                data[column] = data[column].fillna(modes.iloc[0] if not modes.empty else "Unknown")

    data = data.reset_index(drop=True)
    data.to_csv(destination, index=False)
    print(f"Read {original_rows:,} rows from {source.name}.")
    print(f"Removed {duplicate_rows:,} duplicates and {invalid_prices:,} rows with invalid sale prices.")
    print(f"Saved {len(data):,} rows and {len(data.columns)} columns to {destination.resolve()}")
    return data


# %%
if __name__ == "__main__":
    cleaned_data = clean_ames_housing()
