"""Dataset profiling and robust type inference."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_round(value, nd=4):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
        return round(float(value), nd)
    except Exception:
        return None


def _detect_kinds(df: pd.DataFrame) -> dict[str, list[str]]:
    numeric: list[str] = []
    categorical: list[str] = []
    datetime: list[str] = []

    for col in df.columns:
        s = df[col]

        if pd.api.types.is_datetime64_any_dtype(s):
            datetime.append(col)
            continue

        # Numeric dtype first.
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            numeric.append(col)
            continue

        if pd.api.types.is_bool_dtype(s):
            categorical.append(col)
            continue

        # Safely infer numeric strings. Require 95% of non-empty values to parse.
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            non_null = s.dropna()
            if len(non_null):
                numeric_candidate = pd.to_numeric(
                    non_null.astype(str).str.replace(",", "", regex=False).str.strip(),
                    errors="coerce",
                )
                numeric_ratio = float(numeric_candidate.notna().mean())
                if numeric_ratio >= 0.95 and numeric_candidate.nunique() > 1:
                    df[col] = pd.to_numeric(
                        s.astype(str).str.replace(",", "", regex=False).str.strip(),
                        errors="coerce",
                    )
                    numeric.append(col)
                    continue

                # Date detection: require 85% parse success and avoid obvious
                # low-cardinality categorical strings.
                sample = non_null.astype(str).head(500)
                try:
                    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                    date_ratio = float(parsed.notna().mean())
                    if date_ratio >= 0.85 and parsed.nunique() > 1:
                        df[col] = pd.to_datetime(s, errors="coerce", format="mixed")
                        datetime.append(col)
                        continue
                except Exception:
                    pass

        categorical.append(col)

    return {
        "numeric": numeric,
        "categorical": categorical,
        "datetime": datetime,
    }


def build_profile(df: pd.DataFrame, name: str, size_bytes: int) -> dict:
    kinds = _detect_kinds(df)

    n_rows = int(len(df))
    n_cols = int(df.shape[1])
    cells = n_rows * n_cols

    missing_total = int(df.isna().sum().sum())
    missing_pct = round(missing_total / cells * 100, 2) if cells else 0.0
    duplicates = int(df.duplicated().sum())
    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)

    constant_cols = [
        str(c) for c in df.columns
        if df[c].nunique(dropna=False) <= 1
    ]

    columns = []

    for col in df.columns:
        s = df[col]

        info = {
            "name": str(col),
            "dtype": str(s.dtype),
            "non_null": int(s.notna().sum()),
            "null_count": int(s.isna().sum()),
            "null_pct": round(float(s.isna().mean()) * 100, 2) if n_rows else 0.0,
            "unique_count": int(s.nunique(dropna=True)),
        }

        if col in kinds["numeric"]:
            numeric = pd.to_numeric(s, errors="coerce").dropna()

            if len(numeric):
                desc = numeric.describe()
                info.update({
                    "kind": "numeric",
                    "mean": _safe_round(desc.get("mean")),
                    "median": _safe_round(numeric.median()),
                    "min": _safe_round(desc.get("min")),
                    "max": _safe_round(desc.get("max")),
                    "std": _safe_round(numeric.std()),
                    "q1": _safe_round(desc.get("25%")),
                    "q3": _safe_round(desc.get("75%")),
                    "iqr": _safe_round(
                        desc.get("75%") - desc.get("25%")
                    ),
                })
            else:
                info["kind"] = "numeric"

        elif col in kinds["datetime"]:
            dates = pd.to_datetime(s, errors="coerce")
            mn = dates.min()
            mx = dates.max()
            info.update({
                "kind": "datetime",
                "min_date": mn.isoformat() if pd.notna(mn) else None,
                "max_date": mx.isoformat() if pd.notna(mx) else None,
            })

        else:
            info["kind"] = "categorical"
            vc = s.value_counts(dropna=True).head(10)
            info["top_values"] = [
                {
                    "value": str(idx),
                    "count": int(val),
                    "pct": round(float(val) / n_rows * 100, 2) if n_rows else 0.0,
                }
                for idx, val in vc.items()
            ]

        columns.append(info)

    return {
        "dataset_name": name,
        "file_size_bytes": size_bytes,
        "rows": n_rows,
        "columns": n_cols,
        "numeric_columns": [str(c) for c in kinds["numeric"]],
        "categorical_columns": [str(c) for c in kinds["categorical"]],
        "datetime_columns": [str(c) for c in kinds["datetime"]],
        "missing_values": missing_total,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicates,
        "constant_columns": constant_cols,
        "memory_usage_mb": memory_mb,
        "column_details": columns,
    }
