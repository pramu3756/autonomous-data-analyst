"""Data quality scoring and issue detection."""
from __future__ import annotations

import pandas as pd
import numpy as np


def compute_quality(df: pd.DataFrame, profile: dict) -> dict:
    n_rows = profile["rows"]
    n_cols = profile["columns"]
    numeric_cols = profile["numeric_columns"]
    categorical_cols = profile["categorical_columns"]

    missing_total = profile["missing_values"]
    missing_pct = profile["missing_pct"]
    duplicates = profile["duplicate_rows"]
    constant_cols = profile["constant_columns"]

    # High-cardinality categorical columns (unique ratio > 0.5)
    high_cardinality = []
    for col in categorical_cols:
        series = df[col]
        if n_rows > 0 and series.nunique(dropna=True) / n_rows > 0.5:
            high_cardinality.append(col)

    # Outliers via IQR
    outlier_total = 0
    outlier_columns = []
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        if count > 0:
            outlier_total += count
            outlier_columns.append(col)

    # Invalid numeric values (inf / -inf)
    invalid_numeric = 0
    for col in numeric_cols:
        invalid_numeric += int(np.isinf(df[col]).sum())

    # Invalid date values (NaT after coercion) — already counted in missing
    invalid_dates = 0
    for col in profile["datetime_columns"]:
        invalid_dates += int(df[col].isna().sum())

    # Quality score (0-100)
    score = 100
    # Missing penalty
    score -= min(40, missing_pct * 2)
    # Duplicate penalty
    if n_rows > 0:
        dup_pct = duplicates / n_rows * 100
        score -= min(20, dup_pct * 2)
    # Constant columns penalty
    score -= min(10, len(constant_cols) * 5)
    # Outlier penalty
    if n_rows > 0:
        out_pct = outlier_total / n_rows * 100
        score -= min(20, out_pct * 2)
    # High cardinality penalty
    score -= min(10, len(high_cardinality) * 2)
    score = max(0, int(round(score)))

    issues = []
    if missing_total > 0:
        issues.append(f"Missing values detected in {len([c for c in df.columns if df[c].isna().any()])} column(s).")
    if duplicates > 0:
        issues.append(f"{duplicates} duplicate row(s) found.")
    if constant_cols:
        issues.append(f"{len(constant_cols)} constant column(s) detected: {', '.join(map(str, constant_cols[:5]))}.")
    if high_cardinality:
        issues.append(f"{len(high_cardinality)} high-cardinality categorical column(s): {', '.join(map(str, high_cardinality[:3]))}.")
    if outlier_total > 0:
        issues.append(f"{outlier_total} outlier(s) detected across {len(outlier_columns)} numeric column(s).")
    if invalid_numeric > 0:
        issues.append(f"{invalid_numeric} infinite numeric value(s) found.")
    if not issues:
        issues.append("No major data quality issues detected.")

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
