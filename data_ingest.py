"""
data_ingest.py — Dataset loading and schema inference module for Cohortly.
Contract:
- load_dataset(file_path: str) -> pd.DataFrame
- detect_schema(df: pd.DataFrame) -> dict
"""

import os
from typing import Optional, Dict, Any
import pandas as pd


def load_dataset(file_path: str) -> pd.DataFrame:
    """Accepts .csv, .xlsx, and optionally .sav/.dta. Raises ValueError with a
    clear message on unsupported format or unreadable file.
    """
    if not os.path.exists(file_path):
        raise ValueError(f"Dataset file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        elif ext in [".sav", ".dta"]:
            try:
                import pyreadstat  # type: ignore
            except ImportError as exc:
                raise ValueError(
                    "SPSS/Stata files require the optional package 'pyreadstat'."
                ) from exc
            if ext == ".sav":
                df, _ = pyreadstat.read_sav(file_path)
            else:
                df, _ = pyreadstat.read_dta(file_path)
        else:
            raise ValueError(
                f"Unsupported file format '{ext}'. Cohortly accepts .csv and .xlsx files."
            )
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to read dataset from '{file_path}': {str(e)}") from e

    if df.empty:
        raise ValueError("The provided dataset is empty (0 rows).")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Inspects DataFrame columns and categorizes them."""
    numeric_cols = []
    categorical_cols = []
    binary_cols = []
    time_col: Optional[str] = None
    patient_id_col: Optional[str] = None

    lower_cols = {col.lower(): col for col in df.columns}

    for candidate in ["patient_id", "patientid", "id", "subject_id", "subjectid", "pat_id"]:
        if candidate in lower_cols:
            patient_id_col = lower_cols[candidate]
            break

    for candidate in ["month", "time", "visit", "timepoint", "step", "day", "week"]:
        if candidate in lower_cols:
            time_col = lower_cols[candidate]
            break

    for col in df.columns:
        if col == patient_id_col:
            continue

        series = df[col].dropna()
        unique_vals = set(series.unique())
        n_unique = len(unique_vals)

        is_binary = False
        if n_unique == 2:
            is_binary = True
        elif n_unique == 1 and unique_vals.issubset({0, 1, "0", "1", True, False, "Y", "N", "yes", "no"}):
            is_binary = True

        if is_binary and col != time_col:
            binary_cols.append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    return {
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "binary_cols": binary_cols,
        "time_col": time_col,
        "patient_id_col": patient_id_col,
    }
