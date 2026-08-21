"""Deterministic visualization selection and aggregation."""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd


def _round(value, nd=4):
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), nd)
    except Exception:
        return None


# ============================================================
# BAR
# ============================================================

def _bar(df, cat, num):
    """
    Generate a compact categorical → numeric bar chart.

    Uses pandas groupby directly instead of constructing
    another full DataFrame.
    """

    try:
        grouped = (
            df.groupby(
                cat,
                dropna=True,
                observed=True,
            )[num]
            .mean()
            .sort_values(
                ascending=False
            )
            .head(15)
        )
    except Exception:
        return None

    if grouped.empty:
        return None

    data = [
        {
            "category": str(category),
            "value": _round(value),
        }
        for category, value in grouped.items()
    ]

    del grouped

    return {
        "type": "bar",
        "title": f"Average {num} by {cat}",
        "x_label": cat,
        "y_label": f"Average {num}",
        "data": data,
    }


# ============================================================
# PIE
# ============================================================

def _pie(df, cat):
    """
    Generate a compact categorical distribution chart.
    """

    try:
        vc = (
            df[cat]
            .value_counts(
                dropna=True,
            )
            .head(8)
        )
    except Exception:
        return None

    if len(vc) < 2:
        return None

    data = [
        {
            "category": str(category),
            "value": int(count),
        }
        for category, count in vc.items()
    ]

    del vc

    return {
        "type": "pie",
        "title": f"Distribution of {cat}",
        "x_label": cat,
        "y_label": "Count",
        "data": data,
    }


# ============================================================
# HISTOGRAM
# ============================================================

def _histogram(df, num):
    """
    Generate a histogram using bounded numeric data.

    np.histogram only needs the numeric values, but we avoid
    creating an unnecessary full DataFrame.
    """

    try:
        series = df[num]

        # Numeric columns have already been normalized by
        # data_loader/profiler in the normal pipeline.
        if not pd.api.types.is_numeric_dtype(series):
            series = pd.to_numeric(
                series,
                errors="coerce",
            )

        # Convert to NumPy only once.
        values = series.to_numpy(
            dtype=float,
            na_value=np.nan,
        )

        # Remove NaN values using NumPy.
        values = values[np.isfinite(values)]

    except Exception:
        return None

    if values.size == 0:
        return None

    bins = min(
        30,
        max(
            10,
            int(np.sqrt(values.size)),
        ),
    )

    try:
        counts, edges = np.histogram(
            values,
            bins=bins,
        )
    except Exception:
        return None

    data = [
        {
            "category": (
                f"{_round(edges[i])}–"
                f"{_round(edges[i + 1])}"
            ),
            "value": int(counts[i]),
        }
        for i in range(len(counts))
    ]

    del values
    del counts
    del edges

    return {
        "type": "histogram",
        "title": f"Distribution of {num}",
        "x_label": num,
        "y_label": "Frequency",
        "data": data,
    }


# ============================================================
# BOX PLOT
# ============================================================

def _box(df, cat, num):
    """
    Generate box-plot statistics directly from grouped data.

    Does not construct a second 50K-row DataFrame.
    """

    try:
        grouped = df.groupby(
            cat,
            dropna=True,
            observed=True,
        )[num]
    except Exception:
        return None

    rows = []

    try:
        for category, group in grouped:

            if len(group) < 2:
                continue

            q1 = group.quantile(0.25)
            median = group.median()
            q3 = group.quantile(0.75)

            rows.append({
                "category": str(category),
                "min": _round(group.min()),
                "q1": _round(q1),
                "median": _round(median),
                "q3": _round(q3),
                "max": _round(group.max()),
            })

            # Only the first 10 groups are needed for the chart.
            if len(rows) >= 10:
                break

    except Exception:
        return None

    if not rows:
        return None

    return {
        "type": "box",
        "title": f"{num} by {cat}",
        "x_label": cat,
        "y_label": num,
        "data": rows,
    }


# ============================================================
# LINE
# ============================================================

def _line(df, date_col, num):
    """
    Generate an aggregated time-series chart.

    Only aggregated periods are returned to the frontend.
    """

    dates = df[date_col]

    if not pd.api.types.is_datetime64_any_dtype(
        dates
    ):
        try:
            dates = pd.to_datetime(
                dates,
                errors="coerce",
            )
        except Exception:
            return None

    values = df[num]

    if not pd.api.types.is_numeric_dtype(
        values
    ):
        values = pd.to_numeric(
            values,
            errors="coerce",
        )

    valid_dates = dates.dropna()

    if valid_dates.empty:
        return None

    try:
        span = max(
            0,
            (
                valid_dates.max() -
                valid_dates.min()
            ).days,
        )
    except Exception:
        return None

    if span <= 31:
        freq = "D"
    elif span <= 120:
        freq = "W"
    elif span <= 730:
        freq = "M"
    elif span <= 2190:
        freq = "Q"
    else:
        freq = "Y"

    try:
        periods = dates.dt.to_period(
            freq
        )

        valid_mask = (
            periods.notna() &
            values.notna()
        )

        if not valid_mask.any():
            return None

        grouped = (
            values[valid_mask]
            .groupby(
                periods[valid_mask],
                observed=True,
            )
            .mean()
        )

    except Exception:
        return None

    if len(grouped) < 2:
        return None

    grouped = grouped.head(500)

    data = [
        {
            "date": period.to_timestamp().isoformat(),
            "value": _round(value),
        }
        for period, value in grouped.items()
    ]

    return {
        "type": "line",
        "title": f"{num} over time",
        "x_label": date_col,
        "y_label": num,
        "data": data,
    }


# ============================================================
# SCATTER
# ============================================================

def _scatter(df, a, b):
    """
    Generate a bounded scatter plot.

    IMPORTANT:
    We sample row indices BEFORE constructing the final
    chart arrays, rather than building a full 50K-row
    temporary DataFrame first.
    """

    try:
        total_rows = len(df)

        if total_rows == 0:
            return None

        max_points = 1500

        if total_rows > max_points:
            rng = np.random.default_rng(42)

            indices = rng.choice(
                total_rows,
                size=max_points,
                replace=False,
            )

            x_series = df[a].iloc[indices]
            y_series = df[b].iloc[indices]

        else:
            x_series = df[a]
            y_series = df[b]

        x_values = pd.to_numeric(
            x_series,
            errors="coerce",
        )

        y_values = pd.to_numeric(
            y_series,
            errors="coerce",
        )

        valid = (
            x_values.notna() &
            y_values.notna()
        )

        x_values = x_values[valid]
        y_values = y_values[valid]

        if len(x_values) == 0:
            return None

        data = [
            {
                "x": _round(x),
                "y": _round(y),
            }
            for x, y in zip(
                x_values,
                y_values,
            )
        ]

        return {
            "type": "scatter",
            "title": f"{a} vs {b}",
            "x_label": a,
            "y_label": b,
            "data": data,
        }

    except Exception:
        return None


# ============================================================
# HEATMAP
# ============================================================

def _heatmap(corr):
    if not corr.get("available"):
        return None

    return {
        "type": "heatmap",
        "title": "Correlation Matrix",
        "columns": corr["columns"],
        "matrix": corr["matrix"],
    }


# ============================================================
# GENERAL CHART GENERATION
# ============================================================

def generate_charts(
    df,
    profile,
    corr,
):
    charts = []

    numeric = profile["numeric_columns"]
    categorical = profile["categorical_columns"]
    datetime = profile["datetime_columns"]

    # --------------------------------------------------------
    # 1–3 group comparison charts
    # --------------------------------------------------------

    for cat in categorical:

        try:
            unique = int(
                df[cat].nunique(
                    dropna=True
                )
            )
        except Exception:
            continue

        if (
            2 <= unique <= 15
            and numeric
        ):
            chart = _bar(
                df,
                cat,
                numeric[0],
            )

            if chart:
                charts.append(chart)

            if len(charts) >= 3:
                break

    # --------------------------------------------------------
    # Pie chart
    # --------------------------------------------------------

    if categorical:

        for cat in categorical:

            try:
                unique = int(
                    df[cat].nunique(
                        dropna=True
                    )
                )
            except Exception:
                continue

            if 2 <= unique <= 6:

                chart = _pie(
                    df,
                    cat,
                )

                if chart:
                    charts.append(chart)

                break

    # --------------------------------------------------------
    # Trend charts
    # --------------------------------------------------------

    if datetime:

        for num in numeric[:2]:

            chart = _line(
                df,
                datetime[0],
                num,
            )

            if chart:
                charts.append(chart)

    # --------------------------------------------------------
    # Scatter charts
    # --------------------------------------------------------

    for pair in corr.get(
        "pairs",
        [],
    )[:3]:

        chart = _scatter(
            df,
            pair["a"],
            pair["b"],
        )

        if chart:
            charts.append(chart)

    # --------------------------------------------------------
    # Histograms
    # --------------------------------------------------------

    for num in numeric[:2]:

        chart = _histogram(
            df,
            num,
        )

        if chart:
            charts.append(chart)

    # --------------------------------------------------------
    # Box plot
    # --------------------------------------------------------

    for cat in categorical[:3]:

        try:
            unique = int(
                df[cat].nunique(
                    dropna=True
                )
            )
        except Exception:
            continue

        if (
            2 <= unique <= 10
            and numeric
        ):
            chart = _box(
                df,
                cat,
                numeric[0],
            )

            if chart:
                charts.append(chart)

            break

    # --------------------------------------------------------
    # Heatmap
    # --------------------------------------------------------

    heatmap = _heatmap(corr)

    if heatmap:
        charts.append(heatmap)

    # --------------------------------------------------------
    # Remove duplicate chart titles
    # --------------------------------------------------------

    result = []
    seen = set()

    for chart in charts:

        title = chart.get(
            "title",
            "",
        )

        if title in seen:
            continue

        seen.add(title)
        result.append(chart)

    gc.collect()

    return result[:10]


# ============================================================
# QUESTION-SPECIFIC CHARTS
# ============================================================

def chart_for_question(
    question,
    df,
    profile,
    corr,
    outliers_result,
    trends,
    comparisons,
    intent,
    column=None,
    category=None,
):
    q = question.lower()

    # --------------------------------------------------------
    # Correlation
    # --------------------------------------------------------

    if intent == "correlations":

        charts = []

        strongest = corr.get(
            "strongest"
        )

        if strongest:

            scatter = _scatter(
                df,
                strongest["a"],
                strongest["b"],
            )

            if scatter:
                charts.append(
                    scatter
                )

        heatmap = _heatmap(
            corr
        )

        if heatmap:
            charts.append(
                heatmap
            )

        return charts

    # --------------------------------------------------------
    # Outliers
    # --------------------------------------------------------

    if intent == "outliers":

        if not profile["numeric_columns"]:
            return []

        if column:
            selected_column = column
        elif outliers_result.get("columns"):
            selected_column = (
                outliers_result["columns"][0]
                ["column"]
            )
        else:
            selected_column = (
                profile["numeric_columns"][0]
            )

        chart = _histogram(
            df,
            selected_column,
        )

        return (
            [chart]
            if chart
            else []
        )

    # --------------------------------------------------------
    # Trends
    # --------------------------------------------------------

    if intent == "trends":

        datetime_cols = (
            profile["datetime_columns"]
        )

        if not datetime_cols:
            return []

        date_col = datetime_cols[0]

        target = column

        if not target:

            trend_items = trends.get(
                "trends",
                [],
            )

            if trend_items:
                target = trend_items[0].get(
                    "numeric_column"
                )

        if target:

            chart = _line(
                df,
                date_col,
                target,
            )

            return (
                [chart]
                if chart
                else []
            )

        return []

    # --------------------------------------------------------
    # Distribution
    # --------------------------------------------------------

    if intent == "distribution":

        target = (
            column
            or (
                profile["numeric_columns"][0]
                if profile["numeric_columns"]
                else None
            )
        )

        if target:

            chart = _histogram(
                df,
                target,
            )

            return (
                [chart]
                if chart
                else []
            )

        return []

    # --------------------------------------------------------
    # Comparisons
    # --------------------------------------------------------

    if intent in {
        "average",
        "sum",
        "median",
        "minimum",
        "maximum",
        "count",
        "group_comparison",
        "group_average",
        "comparison",
    }:

        if category and column:

            chart = _bar(
                df,
                category,
                column,
            )

            return (
                [chart]
                if chart
                else []
            )

        if comparisons:

            comparison = comparisons[0]

            chart = _bar(
                df,
                comparison[
                    "category_column"
                ],
                comparison[
                    "numeric_column"
                ],
            )

            return (
                [chart]
                if chart
                else []
            )

        if column:

            chart = _histogram(
                df,
                column,
            )

            return (
                [chart]
                if chart
                else []
            )

    return []