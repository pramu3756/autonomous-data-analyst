"""Data quality scoring and issue detection."""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd


def compute_quality(df: pd.DataFrame, profile: dict) -> dict:
    n_rows = int(profile["rows"])
    numeric_cols = profile["numeric_columns"]
    categorical_cols = profile["categorical_columns"]

    missing_total = int(profile["missing_values"])
    missing_pct = float(profile["missing_pct"])
    duplicates = int(profile["duplicate_rows"])
    constant_cols = profile["constant_columns"]

    # -------------------------------------------------------------
    # Columns containing missing values
    # -------------------------------------------------------------
    # Use the profile that was already calculated instead of scanning
    # the entire DataFrame again.
    missing_columns = [
        item["name"]
        for item in profile.get("column_details", [])
        if item.get("null_count", 0) > 0
    ]

    # -------------------------------------------------------------
    # High-cardinality categorical columns
    # -------------------------------------------------------------
    high_cardinality: list[str] = []

    if n_rows > 0:
        for col in categorical_cols:
            series = df[col]

            unique_count = int(
                series.nunique(dropna=True)
            )

            if unique_count / n_rows > 0.5:
                high_cardinality.append(col)

    # -------------------------------------------------------------
    # Outliers using IQR
    # -------------------------------------------------------------
    outlier_total = 0
    outlier_columns: list[str] = []

    for col in numeric_cols:
        series = df[col]

        # quantile() ignores NaN values, so we don't need
        # to create a separate dropna() copy.
        try:
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
        except Exception:
            continue

        if pd.isna(q1) or pd.isna(q3):
            continue

        iqr = q3 - q1

        if pd.isna(iqr) or iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        # Comparison naturally produces False for NaN values.
        outlier_mask = (
            (series < lower) |
            (series > upper)
        )

        count = int(
            outlier_mask.sum()
        )

        if count > 0:
            outlier_total += count
            outlier_columns.append(col)

        # Explicitly release the temporary boolean mask.
        del outlier_mask

    # -------------------------------------------------------------
    # Invalid numeric values: +inf / -inf
    # -------------------------------------------------------------
    invalid_numeric = 0

    for col in numeric_cols:
        series = df[col]

        try:
            invalid_numeric += int(
                np.isinf(series.to_numpy(copy=False)).sum()
            )
        except (TypeError, ValueError):
            # Defensive fallback for unusual pandas dtypes.
            invalid_numeric += int(
                np.isinf(
                    pd.to_numeric(
                        series,
                        errors="coerce",
                    ).to_numpy()
                ).sum()
            )

    # -------------------------------------------------------------
    # Invalid date values
    # -------------------------------------------------------------
    # Date columns were already normalized by profiler.py.
    # NaT values are represented by isna().
    invalid_dates = 0

    for col in profile["datetime_columns"]:
        invalid_dates += int(
            df[col].isna().sum()
        )

    # -------------------------------------------------------------
    # Quality score
    # -------------------------------------------------------------
    score = 100.0

    # Missing-value penalty
    score -= min(
        40,
        missing_pct * 2,
    )

    # Duplicate penalty
    if n_rows > 0:
        dup_pct = (
            duplicates / n_rows
        ) * 100

        score -= min(
            20,
            dup_pct * 2,
        )

    # Constant-column penalty
    score -= min(
        10,
        len(constant_cols) * 5,
    )

    # Outlier penalty
    if n_rows > 0:
        out_pct = (
            outlier_total / n_rows
        ) * 100

        score -= min(
            20,
            out_pct * 2,
        )

    # High-cardinality penalty
    score -= min(
        10,
        len(high_cardinality) * 2,
    )

    score = max(
        0,
        int(round(score)),
    )

    # -------------------------------------------------------------
    # Human-readable issues
    # -------------------------------------------------------------
    issues: list[str] = []

    if missing_total > 0:
        issues.append(
            f"Missing values detected in "
            f"{len(missing_columns)} column(s)."
        )

    if duplicates > 0:
        issues.append(
            f"{duplicates} duplicate row(s) found."
        )

    if constant_cols:
        issues.append(
            f"{len(constant_cols)} constant column(s) "
            f"detected: "
            f"{', '.join(map(str, constant_cols[:5]))}."
        )

    if high_cardinality:
        issues.append(
            f"{len(high_cardinality)} high-cardinality "
            f"categorical column(s): "
            f"{', '.join(map(str, high_cardinality[:3]))}."
        )

    if outlier_total > 0:
        issues.append(
            f"{outlier_total} outlier(s) detected "
            f"across {len(outlier_columns)} "
            f"numeric column(s)."
        )

    if invalid_numeric > 0:
        issues.append(
            f"{invalid_numeric} infinite numeric "
            f"value(s) found."
        )

    if not issues:
        issues.append(
            "No major data quality issues detected."
        )

    # Release local temporary references before returning.
    gc.collect()

    return {
        "score": score,
        "missing_values": missing_total,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicates,
        "outliers": outlier_total,
        "outlier_columns": outlier_columns,
        "constant_columns": constant_cols,
        "high_cardinality": high_cardinality,
        "invalid_numeric": invalid_numeric,
        "invalid_dates": invalid_dates,
        "issues": issues,
    }