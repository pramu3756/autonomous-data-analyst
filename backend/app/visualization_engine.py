"""Deterministic visualization selection and aggregation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _round(value, nd=4):
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), nd)
    except Exception:
        return None


def _bar(df, cat, num):
    temp = pd.DataFrame({
        "_cat": df[cat],
        "_value": pd.to_numeric(df[num], errors="coerce"),
    }).dropna()

    if temp.empty:
        return None

    grouped = (
        temp.groupby("_cat")["_value"]
        .mean()
        .sort_values(ascending=False)
        .head(15)
    )

    return {
        "type": "bar",
        "title": f"Average {num} by {cat}",
        "x_label": cat,
        "y_label": f"Average {num}",
        "data": [
            {"category": str(k), "value": _round(v)}
            for k, v in grouped.items()
        ],
    }


def _pie(df, cat):
    vc = df[cat].value_counts(dropna=True).head(8)
    if len(vc) < 2:
        return None

    return {
        "type": "pie",
        "title": f"Distribution of {cat}",
        "x_label": cat,
        "y_label": "Count",
        "data": [
            {"category": str(k), "value": int(v)}
            for k, v in vc.items()
        ],
    }


def _histogram(df, num):
    values = pd.to_numeric(df[num], errors="coerce").dropna()
    if values.empty:
        return None

    bins = min(30, max(10, int(np.sqrt(len(values)))))
    counts, edges = np.histogram(values.to_numpy(), bins=bins)

    return {
        "type": "histogram",
        "title": f"Distribution of {num}",
        "x_label": num,
        "y_label": "Frequency",
        "data": [
            {
                "category": f"{_round(edges[i])}–{_round(edges[i + 1])}",
                "value": int(counts[i]),
            }
            for i in range(len(counts))
        ],
    }


def _box(df, cat, num):
    temp = pd.DataFrame({
        "_cat": df[cat],
        "_value": pd.to_numeric(df[num], errors="coerce"),
    }).dropna()

    if temp.empty:
        return None

    rows = []
    for category, group in temp.groupby("_cat")["_value"]:
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

    if not rows:
        return None

    return {
        "type": "box",
        "title": f"{num} by {cat}",
        "x_label": cat,
        "y_label": num,
        "data": rows[:10],
    }


def _line(df, date_col, num):
    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[num], errors="coerce")

    temp = pd.DataFrame({
        "_date": dates,
        "_value": values,
    }).dropna()

    if temp.empty:
        return None

    span = max(
        0,
        (temp["_date"].max() - temp["_date"].min()).days,
    )

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

    temp["_period"] = temp["_date"].dt.to_period(freq).dt.to_timestamp()
    grouped = temp.groupby("_period")["_value"].mean()

    if len(grouped) < 2:
        return None

    return {
        "type": "line",
        "title": f"{num} over time",
        "x_label": date_col,
        "y_label": num,
        "data": [
            {"date": idx.isoformat(), "value": _round(v)}
            for idx, v in grouped.head(500).items()
        ],
    }


def _scatter(df, a, b):
    temp = pd.DataFrame({
        "_x": pd.to_numeric(df[a], errors="coerce"),
        "_y": pd.to_numeric(df[b], errors="coerce"),
    }).dropna()

    if temp.empty:
        return None

    # Render at most 1500 points; analysis itself still uses all rows.
    if len(temp) > 1500:
        temp = temp.sample(1500, random_state=42)

    return {
        "type": "scatter",
        "title": f"{a} vs {b}",
        "x_label": a,
        "y_label": b,
        "data": [
            {"x": _round(x), "y": _round(y)}
            for x, y in zip(temp["_x"], temp["_y"])
        ],
    }


def _heatmap(corr):
    if not corr.get("available"):
        return None

    return {
        "type": "heatmap",
        "title": "Correlation Matrix",
        "columns": corr["columns"],
        "matrix": corr["matrix"],
    }


def generate_charts(df, profile, corr):
    charts = []
    numeric = profile["numeric_columns"]
    categorical = profile["categorical_columns"]
    datetime = profile["datetime_columns"]

    # 1–3 useful group comparisons.
    for cat in categorical:
        unique = df[cat].nunique(dropna=True)
        if 2 <= unique <= 15 and numeric:
            chart = _bar(df, cat, numeric[0])
            if chart:
                charts.append(chart)
            if len(charts) >= 3:
                break

    # One compact composition chart.
    if categorical:
        for cat in categorical:
            unique = df[cat].nunique(dropna=True)
            if 2 <= unique <= 6:
                chart = _pie(df, cat)
                if chart:
                    charts.append(chart)
                    break

    # Trend charts.
    if datetime:
        for num in numeric[:2]:
            chart = _line(df, datetime[0], num)
            if chart:
                charts.append(chart)

    # Strong correlation scatter charts.
    for pair in corr.get("pairs", [])[:3]:
        chart = _scatter(df, pair["a"], pair["b"])
        if chart:
            charts.append(chart)

    # Distributions.
    for num in numeric[:2]:
        chart = _histogram(df, num)
        if chart:
            charts.append(chart)

    # Box plot for a useful categorical grouping.
    for cat in categorical[:3]:
        unique = df[cat].nunique(dropna=True)
        if 2 <= unique <= 10 and numeric:
            chart = _box(df, cat, numeric[0])
            if chart:
                charts.append(chart)
                break

    heatmap = _heatmap(corr)
    if heatmap:
        charts.append(heatmap)

    # Remove duplicate titles and keep a useful maximum.
    result = []
    seen = set()
    for chart in charts:
        title = chart.get("title", "")
        if title in seen:
            continue
        seen.add(title)
        result.append(chart)

    return result[:10]


def chart_for_question(question, df, profile, corr, outliers_result, trends, comparisons, intent, column=None, category=None):
    q = question.lower()

    if intent == "correlations":
        # Prefer the strongest relationship for a scatter plot plus matrix.
        charts = []
        strongest = corr.get("strongest")
        if strongest:
            scatter = _scatter(df, strongest["a"], strongest["b"])
            if scatter:
                charts.append(scatter)
        heatmap = _heatmap(corr)
        if heatmap:
            charts.append(heatmap)
        return charts

    if intent == "outliers":
        if not profile["numeric_columns"]:
            return []
        col = column or outliers_result["columns"][0]["column"]
        return [c for c in [_histogram(df, col)] if c]

    if intent == "trends":
        date_col = profile["datetime_columns"][0] if profile["datetime_columns"] else None
        if not date_col:
            return []
        target = column or (
            trends.get("trends", [{}])[0].get("numeric_column")
            if trends.get("trends") else None
        )
        if target:
            chart = _line(df, date_col, target)
            return [chart] if chart else []
        return []

    if intent in {"distribution"}:
        target = column or (profile["numeric_columns"][0] if profile["numeric_columns"] else None)
        if target:
            chart = _histogram(df, target)
            return [chart] if chart else []
        return []

    if intent in {"average", "sum", "median", "minimum", "maximum", "count", "group_comparison", "group_average", "comparison"}:
        if category and column:
            chart = _bar(df, category, column)
            return [chart] if chart else []

        # Infer from the selected comparison.
        if comparisons:
            c = comparisons[0]
            chart = _bar(df, c["category_column"], c["numeric_column"])
            return [chart] if chart else []

        if column:
            chart = _histogram(df, column)
            return [chart] if chart else []

    return []
