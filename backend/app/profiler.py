"""Dataset profiling with memory-conscious type inference."""
from __future__ import annotations

import gc

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
    """
    Detect numeric, categorical and datetime columns.

    Important:
    - Do not convert every object column to strings.
    - Only perform expensive conversions when a column is a candidate.
    - Avoid retaining temporary Series longer than necessary.
    """

    numeric: list[str] = []
    categorical: list[str] = []
    datetime: list[str] = []

    for col in df.columns:
        s = df[col]
        dtype = s.dtype

        # Already datetime.
        if pd.api.types.is_datetime64_any_dtype(dtype):
            datetime.append(col)
            continue

        # Already numeric.
        if (
            pd.api.types.is_numeric_dtype(dtype)
            and not pd.api.types.is_bool_dtype(dtype)
        ):
            numeric.append(col)
            continue

        # Boolean → categorical.
        if pd.api.types.is_bool_dtype(dtype):
            categorical.append(col)
            continue

        # Object/string inference.
        if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
            non_null = s.dropna()

            if len(non_null):
                # ---------------------------------------------------------
                # Numeric detection
                # ---------------------------------------------------------
                try:
                    sample = non_null.head(1000)

                    numeric_sample = pd.to_numeric(
                        sample.astype(str)
                        .str.replace(",", "", regex=False)
                        .str.strip(),
                        errors="coerce",
                    )

                    numeric_ratio = float(
                        numeric_sample.notna().mean()
                    )

                    is_numeric = (
                        numeric_ratio >= 0.95
                        and numeric_sample.nunique(dropna=True) > 1
                    )

                    del numeric_sample

                    if is_numeric:
                        # Convert the actual column only after classification.
                        converted = pd.to_numeric(
                            s.astype(str)
                            .str.replace(",", "", regex=False)
                            .str.strip(),
                            errors="coerce",
                        )

                        df[col] = converted

                        del converted
                        del non_null

                        numeric.append(col)
                        continue

                except Exception:
                    pass

                # ---------------------------------------------------------
                # Datetime detection
                # ---------------------------------------------------------
                try:
                    date_sample = non_null.head(500).astype(str)

                    parsed_sample = pd.to_datetime(
                        date_sample,
                        errors="coerce",
                        format="mixed",
                    )

                    date_ratio = float(
                        parsed_sample.notna().mean()
                    )

                    is_datetime = (
                        date_ratio >= 0.85
                        and parsed_sample.nunique(dropna=True) > 1
                    )

                    del date_sample
                    del parsed_sample

                    if is_datetime:
                        converted_dates = pd.to_datetime(
                            s,
                            errors="coerce",
                            format="mixed",
                        )

                        df[col] = converted_dates

                        del converted_dates
                        del non_null

                        datetime.append(col)
                        continue

                except Exception:
                    pass

            del non_null

        categorical.append(col)

    gc.collect()

    return {
        "numeric": numeric,
        "categorical": categorical,
        "datetime": datetime,
    }


def build_profile(
    df: pd.DataFrame,
    name: str,
    size_bytes: int,
) -> dict:
    """
    Build a compact dataset profile while minimizing peak memory usage.
    """

    kinds = _detect_kinds(df)

    n_rows = int(len(df))
    n_cols = int(df.shape[1])
    cells = n_rows * n_cols

    # -------------------------------------------------------------
    # Missing values
    # -------------------------------------------------------------
    missing_total = 0

    for col in df.columns:
        missing_total += int(df[col].isna().sum())

    missing_pct = (
        round((missing_total / cells) * 100, 2)
        if cells
        else 0.0
    )

    # -------------------------------------------------------------
    # Duplicate rows
    # -------------------------------------------------------------
    # duplicated() creates a boolean array. This is considerably
    # smaller than copying the entire DataFrame.
    duplicates = int(df.duplicated().sum())

    # -------------------------------------------------------------
    # Memory usage
    # -------------------------------------------------------------
    memory_bytes = int(
        df.memory_usage(deep=True).sum()
    )

    memory_mb = round(
        memory_bytes / (1024 * 1024),
        2,
    )

    # -------------------------------------------------------------
    # Constant columns
    # -------------------------------------------------------------
    constant_cols: list[str] = []

    for col in df.columns:
        if df[col].nunique(dropna=False) <= 1:
            constant_cols.append(str(col))

    # -------------------------------------------------------------
    # Column details
    # -------------------------------------------------------------
    columns: list[dict] = []

    numeric_set = set(kinds["numeric"])
    datetime_set = set(kinds["datetime"])

    for col in df.columns:
        s = df[col]

        null_count = int(s.isna().sum())
        non_null_count = n_rows - null_count

        unique_count = int(
            s.nunique(dropna=True)
        )

        info = {
            "name": str(col),
            "dtype": str(s.dtype),
            "non_null": non_null_count,
            "null_count": null_count,
            "null_pct": (
                round(
                    (null_count / n_rows) * 100,
                    2,
                )
                if n_rows
                else 0.0
            ),
            "unique_count": unique_count,
        }

        # =============================================================
        # NUMERIC
        # =============================================================
        if col in numeric_set:

            numeric_s = pd.to_numeric(
                s,
                errors="coerce",
            )

            valid_count = int(
                numeric_s.notna().sum()
            )

            if valid_count:

                # Use pandas aggregation without creating
                # a full `describe()` result.
                mean_value = numeric_s.mean()
                median_value = numeric_s.median()
                min_value = numeric_s.min()
                max_value = numeric_s.max()
                std_value = numeric_s.std()

                q1 = numeric_s.quantile(0.25)
                q3 = numeric_s.quantile(0.75)

                info.update(
                    {
                        "kind": "numeric",
                        "mean": _safe_round(mean_value),
                        "median": _safe_round(median_value),
                        "min": _safe_round(min_value),
                        "max": _safe_round(max_value),
                        "std": _safe_round(std_value),
                        "q1": _safe_round(q1),
                        "q3": _safe_round(q3),
                        "iqr": _safe_round(
                            q3 - q1
                        ),
                    }
                )

                del mean_value
                del median_value
                del min_value
                del max_value
                del std_value
                del q1
                del q3

            else:
                info["kind"] = "numeric"

            del numeric_s

        # =============================================================
        # DATETIME
        # =============================================================
        elif col in datetime_set:

            dates = s

            mn = dates.min()
            mx = dates.max()

            info.update(
                {
                    "kind": "datetime",
                    "min_date": (
                        mn.isoformat()
                        if pd.notna(mn)
                        else None
                    ),
                    "max_date": (
                        mx.isoformat()
                        if pd.notna(mx)
                        else None
                    ),
                }
            )

            del dates

        # =============================================================
        # CATEGORICAL
        # =============================================================
        else:

            info["kind"] = "categorical"

            # Only keep the top 10 values.
            vc = (
                s.value_counts(
                    dropna=True,
                )
                .head(10)
            )

            info["top_values"] = [
                {
                    "value": str(idx),
                    "count": int(val),
                    "pct": (
                        round(
                            (float(val) / n_rows) * 100,
                            2,
                        )
                        if n_rows
                        else 0.0
                    ),
                }
                for idx, val in vc.items()
            ]

            del vc

        columns.append(info)

        # Encourage release of temporary objects
        # before moving to the next column.
        gc.collect()

    result = {
        "dataset_name": name,
        "file_size_bytes": size_bytes,
        "rows": n_rows,
        "columns": n_cols,
        "numeric_columns": [
            str(c)
            for c in kinds["numeric"]
        ],
        "categorical_columns": [
            str(c)
            for c in kinds["categorical"]
        ],
        "datetime_columns": [
            str(c)
            for c in kinds["datetime"]
        ],
        "missing_values": missing_total,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicates,
        "constant_columns": constant_cols,
        "memory_usage_mb": memory_mb,
        "column_details": columns,
    }

    del kinds
    gc.collect()

    return result