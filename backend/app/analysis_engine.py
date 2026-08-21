"""Deterministic analysis engine. No LLM/API dependency."""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd


def _round(value, nd=4):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
        return round(float(value), nd)
    except Exception:
        return None


def numeric_stats(df, numeric_cols):
    """
    Calculate numeric statistics without creating unnecessary
    copies of the full column.
    """
    results = []

    for col in numeric_cols:
        # profiler.py already converted numeric columns.
        s = df[col]

        if s.empty:
            continue

        # Pandas statistical operations ignore NaN values.
        count = int(s.notna().sum())

        if count == 0:
            continue

        mean = s.mean()
        median = s.median()
        minimum = s.min()
        maximum = s.max()
        std = s.std()
        variance = s.var()
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)

        skewness = None

        if count > 2:
            try:
                # scipy is avoided here because pandas can calculate
                # skewness without creating a dropna() copy.
                skewness = s.skew()
            except Exception:
                skewness = None

        results.append({
            "column": col,
            "mean": _round(mean),
            "median": _round(median),
            "min": _round(minimum),
            "max": _round(maximum),
            "std": _round(std),
            "variance": _round(variance),
            "range": _round(maximum - minimum),
            "q1": _round(q1),
            "q3": _round(q3),
            "iqr": _round(q3 - q1),
            "skewness": _round(skewness),
        })

    return results


def correlations(df, numeric_cols, max_columns=20):
    """
    Calculate correlations using at most max_columns numeric columns.
    This keeps memory usage bounded for wide datasets.
    """

    valid = []

    for col in numeric_cols:
        s = df[col]

        if int(s.notna().sum()) >= 2:
            if s.nunique(dropna=True) > 1:
                valid.append(col)

    if len(valid) > max_columns:
        # Calculate variance one column at a time instead of using
        # DataFrame.apply() over a large temporary DataFrame.
        variance_values = []

        for col in valid:
            try:
                variance_values.append(
                    (col, float(df[col].var()))
                )
            except Exception:
                variance_values.append(
                    (col, 0.0)
                )

        variance_values.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        valid = [
            col
            for col, _ in variance_values[:max_columns]
        ]

    if len(valid) < 2:
        return {
            "available": False,
            "message": (
                "At least two varying numerical columns are "
                "required for correlation analysis."
            ),
            "columns": [],
            "matrix": [],
            "pairs": [],
            "strongest": None,
            "strongest_positive": None,
            "strongest_negative": None,
        }

    # Maximum size here is 50,000 × 20.
    # This is bounded and therefore safe compared with processing
    # all 200 columns.
    corr_df = df[valid].corr()

    columns = list(corr_df.columns)

    matrix = [
        [
            _round(corr_df.iloc[i, j])
            for j in range(len(columns))
        ]
        for i in range(len(columns))
    ]

    pairs = []

    for i, a in enumerate(columns):
        for j in range(i + 1, len(columns)):
            b = columns[j]

            value = corr_df.iloc[i, j]

            if pd.isna(value):
                continue

            value = float(value)
            absolute = abs(value)

            if absolute >= 0.70:
                strength = "strong"
            elif absolute >= 0.40:
                strength = "moderate"
            else:
                strength = "weak"

            pairs.append({
                "a": a,
                "b": b,
                "correlation": _round(value),
                "strength": strength,
            })

    pairs.sort(
        key=lambda x: abs(x["correlation"]),
        reverse=True,
    )

    strongest_positive = next(
        (
            p for p in pairs
            if p["correlation"] > 0
        ),
        None,
    )

    strongest_negative = next(
        (
            p for p in pairs
            if p["correlation"] < 0
        ),
        None,
    )

    result = {
        "available": True,
        "columns": columns,
        "matrix": matrix,
        "pairs": pairs[:100],
        "strongest": pairs[0] if pairs else None,
        "strongest_positive": strongest_positive,
        "strongest_negative": strongest_negative,
    }

    # Release the bounded correlation DataFrame.
    del corr_df

    return result


def outliers(df, numeric_cols):
    """
    IQR outlier detection without explicit dropna() copies.
    """
    results = []
    total = 0

    for col in numeric_cols:
        s = df[col]

        if int(s.notna().sum()) == 0:
            continue

        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)

        if pd.isna(q1) or pd.isna(q3):
            continue

        iqr = q3 - q1

        if iqr == 0:
            lower = q1
            upper = q3
            count = 0
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            # NaN comparisons return False.
            mask = (
                (s < lower) |
                (s > upper)
            )

            count = int(mask.sum())

            del mask

        total += count

        non_null_count = int(s.notna().sum())

        results.append({
            "column": col,
            "count": count,
            "pct": _round(
                count / non_null_count * 100,
                2,
            ) if non_null_count else 0,
            "lower_bound": _round(lower),
            "upper_bound": _round(upper),
            "q1": _round(q1),
            "q3": _round(q3),
            "iqr": _round(iqr),
        })

    results.sort(
        key=lambda x: x["count"],
        reverse=True,
    )

    return {
        "total_outliers": total,
        "columns": results,
    }


def group_comparisons(
    df,
    numeric_cols,
    categorical_cols,
    max_comparisons=12,
):
    """
    Compare categorical groups without constructing a temporary
    DataFrame containing the full dataset for every comparison.
    """

    comparisons = []

    # Keep numeric analysis bounded.
    selected_numeric = numeric_cols[:6]

    for cat in categorical_cols:

        series_cat = df[cat]

        unique = int(
            series_cat.nunique(dropna=True)
        )

        if unique < 2 or unique > 30:
            continue

        for num in selected_numeric:

            series_num = df[num]

            try:
                # Group directly on the original columns.
                grouped = (
                    df.groupby(
                        cat,
                        dropna=True,
                        observed=True,
                    )[num]
                    .agg(
                        ["count", "mean", "median", "min", "max"]
                    )
                    .sort_values(
                        "mean",
                        ascending=False,
                    )
                    .head(20)
                    .reset_index()
                )
            except Exception:
                continue

            if grouped.empty:
                continue

            rows = []

            for _, row in grouped.iterrows():
                category = row.iloc[0]

                rows.append({
                    "category": str(category),
                    "count": int(row["count"]),
                    "mean": _round(row["mean"]),
                    "median": _round(row["median"]),
                    "min": _round(row["min"]),
                    "max": _round(row["max"]),
                })

            comparisons.append({
                "category_column": cat,
                "numeric_column": num,
                "title": f"Average {num} by {cat}",
                "data": rows,
            })

            del grouped

            if len(comparisons) >= max_comparisons:
                return comparisons

    return comparisons


def trend_analysis(
    df,
    numeric_cols,
    datetime_cols,
):
    """
    Perform trend analysis without creating one large temporary
    DataFrame for every numeric column.
    """

    if not datetime_cols:
        return {
            "available": False,
            "message": (
                "No date column was detected, so trend analysis "
                "is unavailable."
            ),
            "trends": [],
        }

    date_col = datetime_cols[0]

    dates = df[date_col]

    valid_dates = dates.dropna()

    if valid_dates.empty:
        return {
            "available": False,
            "message": "No valid date values were found.",
            "trends": [],
        }

    span_days = max(
        0,
        (
            valid_dates.max() -
            valid_dates.min()
        ).days,
    )

    if span_days <= 31:
        freq = "D"
        label = "daily"
    elif span_days <= 120:
        freq = "W"
        label = "weekly"
    elif span_days <= 730:
        freq = "M"
        label = "monthly"
    elif span_days <= 2190:
        freq = "Q"
        label = "quarterly"
    else:
        freq = "Y"
        label = "yearly"

    # Calculate period once.
    periods = dates.dt.to_period(freq)

    trend_list = []

    for num in numeric_cols[:8]:

        values = df[num]

        # Group directly using the period Series.
        valid_mask = (
            periods.notna() &
            values.notna()
        )

        if not valid_mask.any():
            continue

        grouped = (
            values[valid_mask]
            .groupby(periods[valid_mask])
            .mean()
        )

        if len(grouped) < 2:
            continue

        numeric_values = grouped.to_numpy(
            dtype=float,
            copy=False,
        )

        x = np.arange(
            len(numeric_values),
            dtype=float,
        )

        try:
            slope = float(
                np.polyfit(
                    x,
                    numeric_values,
                    1,
                )[0]
            )
        except Exception:
            slope = 0.0

        if slope > 0:
            direction = "upward"
        elif slope < 0:
            direction = "downward"
        else:
            direction = "flat"

        # Maximum 500 chart points.
        grouped = grouped.head(500)

        series = [
            {
                "date": period.to_timestamp().isoformat(),
                "value": _round(value),
            }
            for period, value in grouped.items()
        ]

        trend_list.append({
            "numeric_column": num,
            "frequency": label,
            "direction": direction,
            "series": series,
        })

        del grouped

    del periods

    return {
        "available": bool(trend_list),
        "date_column": date_col,
        "frequency": label,
        "trends": trend_list,
    }


def key_findings(
    df,
    profile,
    corr,
    outl,
    trends,
    comparisons,
):
    findings = [
        {
            "id": 1,
            "text": (
                f"The dataset contains "
                f"{profile['rows']:,} records "
                f"across {profile['columns']} columns."
            ),
        }
    ]

    if profile["missing_pct"] > 0:
        findings.append({
            "id": 2,
            "text": (
                f"Missing values affect "
                f"{profile['missing_pct']}% "
                "of all dataset cells."
            ),
        })

    if corr.get("strongest"):
        s = corr["strongest"]

        findings.append({
            "id": 3,
            "text": (
                f"{s['a']} and {s['b']} have a "
                f"{s['strength']} Pearson correlation "
                f"(r={s['correlation']})."
            ),
        })

    if outl["total_outliers"] > 0:
        top = (
            outl["columns"][0]
            if outl["columns"]
            else None
        )

        text = (
            f"{outl['total_outliers']:,} "
            "outlier values were detected"
        )

        if top:
            text += (
                f", with {top['count']:,} "
                f"in {top['column']}"
            )

        findings.append({
            "id": 4,
            "text": text + ".",
        })

    if comparisons and comparisons[0]["data"]:
        comparison = comparisons[0]
        top = comparison["data"][0]

        findings.append({
            "id": 5,
            "text": (
                f"{top['category']} has the highest "
                f"average {comparison['numeric_column']} "
                f"({top['mean']}) among "
                f"{comparison['category_column']} groups."
            ),
        })

    if trends.get("available") and trends.get("trends"):
        trend = trends["trends"][0]

        findings.append({
            "id": 6,
            "text": (
                f"{trend['numeric_column']} shows an "
                f"{trend['direction']} trend at "
                f"{trend['frequency']} frequency."
            ),
        })

    return findings[:6]


def build_summary(
    df,
    profile,
    corr,
    comparisons,
):
    parts = [
        (
            f"The dataset contains "
            f"{profile['rows']:,} records across "
            f"{profile['columns']} columns, with "
            f"{len(profile['numeric_columns'])} numeric, "
            f"{len(profile['categorical_columns'])} categorical, "
            f"and {len(profile['datetime_columns'])} "
            "date/time features."
        )
    ]

    if profile["missing_pct"] > 0:
        parts.append(
            f"Missing values account for "
            f"{profile['missing_pct']}% of cells."
        )

    if profile["duplicate_rows"] > 0:
        parts.append(
            f"There are "
            f"{profile['duplicate_rows']:,} duplicate rows."
        )

    if corr.get("strongest"):
        s = corr["strongest"]

        parts.append(
            f"{s['a']} and {s['b']} have the strongest "
            f"observed relationship "
            f"(r={s['correlation']})."
        )

    if comparisons:
        parts.append(
            f"{len(comparisons)} useful "
            "category-to-numeric comparisons "
            "were identified."
        )

    return " ".join(parts)