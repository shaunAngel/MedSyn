"""Dataset loading and conservative schema detection."""
from pathlib import Path
import pandas as pd


def load_dataset(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Unsupported format. Please provide a CSV or XLSX file.")


def detect_schema(df: pd.DataFrame) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    numeric = list(df.select_dtypes(include="number").columns)
    binary = [c for c in numeric if set(df[c].dropna().unique()).issubset({0, 1})]
    patient = next((c for c in df if "patient" in c.lower() and "id" in c.lower()), None)
    time = next((c for c in df if c.lower() in {"month", "date", "time", "timestamp"}), None)
    return {"numeric_cols": numeric, "categorical_cols": [c for c in df if c not in numeric], "binary_cols": binary, "time_col": time, "patient_id_col": patient}
