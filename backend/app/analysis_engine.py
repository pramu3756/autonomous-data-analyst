"""Deterministic analysis engine. No LLM/API dependency."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats


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
    results = []
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        results.append({
            "column": col,
            "mean": _round(s.mean()),
            "median": _round(s.median()),
            "min": _round(s.min()),
            "max": _round(s.max()),
            "std": _round(s.std()),
            "variance": _round(s.var()),
            "range": _round(s.max() - s.min()),
            "q1": _round(q1),
            "q3": _round(q3),
            "iqr": _round(q3 - q1),
            "skewness": _round(sp_stats.skew(s, bias=False)) if len(s) > 2 else None,
        })
    return results


def correlations(df, numeric_cols, max_columns=20):
    valid = []
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() >= 2 and s.nunique(dropna=True) > 1:
            valid.append(col)

    # Keep the most informative columns for the heatmap if a very wide
    # dataset is uploaded. Pair analysis remains bounded as well.
    if len(valid) > max_columns:
        variances = df[valid].apply(
            lambda s: pd.to_numeric(s, errors="coerce").var()
        ).sort_values(ascending=False)
        valid = list(variances.head(max_columns).index)

    if len(valid) < 2:
        return {
            "available": False,
            "message": "At least two varying numerical columns are required for correlation analysis.",
            "columns": [],
            "matrix": [],
            "pairs": [],
            "strongest": None,
            "strongest_positive": None,
            "strongest_negative": None,
        }

    corr_df = df[valid].apply(pd.to_numeric, errors="coerce").corr()
    columns = list(corr_df.columns)
    matrix = [
        [_round(corr_df.loc[r, c]) for c in columns]
        for r in columns
    ]

    pairs = []
    for i, a in enumerate(columns):
        for b in columns[i + 1:]:
            value = corr_df.loc[a, b]
            if pd.isna(value):
                continue
            av = abs(float(value))
            strength = (
                "strong" if av >= 0.70
                else "moderate" if av >= 0.40
                else "weak"
            )
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

    return {
        "available": True,
        "columns": columns,
        "matrix": matrix,
        "pairs": pairs[:100],
        "strongest": pairs[0] if pairs else None,
        "strongest_positive": next(
            (p for p in pairs if p["correlation"] > 0), None
        ),
        "strongest_negative": next(
            (p for p in pairs if p["correlation"] < 0), None
        ),
    }


def outliers(df, numeric_cols):
    results = []
    total = 0

    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue

        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0 or pd.isna(iqr):
            count = 0
            lower = q1
            upper = q3
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            count = int(((s < lower) | (s > upper)).sum())

        total += count

        results.append({
            "column": col,
            "count": count,
            "pct": _round(count / len(s) * 100, 2),
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
    comparisons = []

    # Avoid Cartesian explosion on wide datasets.
    for cat in categorical_cols:
        unique = df[cat].nunique(dropna=True)
        if unique < 2 or unique > 30:
            continue

        for num in numeric_cols[:6]:
            series = pd.to_numeric(df[num], errors="coerce")
            temp = pd.DataFrame({
                "_cat": df[cat],
                "_num": series,
            }).dropna(subset=["_cat", "_num"])

            if temp.empty:
                continue

            agg = (
                temp.groupby("_cat")["_num"]
                .agg(["count", "mean", "median", "min", "max"])
                .sort_values("mean", ascending=False)
                .head(20)
                .reset_index()
            )

            rows = [
                {
                    "category": str(row["_cat"]),
                    "count": int(row["count"]),
                    "mean": _round(row["mean"]),
                    "median": _round(row["median"]),
                    "min": _round(row["min"]),
                    "max": _round(row["max"]),
                }
                for _, row in agg.iterrows()
            ]

            comparisons.append({
                "category_column": cat,
                "numeric_column": num,
                "title": f"Average {num} by {cat}",
                "data": rows,
            })

            if len(comparisons) >= max_comparisons:
                return comparisons

    return comparisons


def trend_analysis(df, numeric_cols, datetime_cols):
    if not datetime_cols:
        return {
            "available": False,
            "message": "No date column was detected, so trend analysis is unavailable.",
            "trends": [],
        }

    date_col = datetime_cols[0]
    dates = pd.to_datetime(df[date_col], errors="coerce")

    valid_mask = dates.notna()
    if not valid_mask.any():
        return {
            "available": False,
            "message": "No valid date values were found.",
            "trends": [],
        }

    span_days = max(
        0,
        (dates[valid_mask].max() - dates[valid_mask].min()).days,
    )

    if span_days <= 31:
        freq, label = "D", "daily"
    elif span_days <= 120:
        freq, label = "W", "weekly"
    elif span_days <= 730:
        freq, label = "M", "monthly"
    elif span_days <= 2190:
        freq, label = "Q", "quarterly"
    else:
        freq, label = "Y", "yearly"

    temp = pd.DataFrame({"_date": dates})
    for num in numeric_cols[:8]:
        temp["_value"] = pd.to_numeric(df[num], errors="coerce")
        temp["_period"] = temp["_date"].dt.to_period(freq).dt.to_timestamp()

        grouped = (
            temp.dropna(subset=["_period", "_value"])
            .groupby("_period")["_value"]
            .mean()
        )

        if len(grouped) < 2:
            continue

        values = grouped.to_numpy(dtype=float)
        slope = float(np.polyfit(np.arange(len(values)), values, 1)[0]) if len(values) >= 2 else 0.0
        direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"

        trends = []
        for idx, value in grouped.items():
            trends.append({
                "date": idx.isoformat(),
                "value": _round(value),
            })

        # Return enough points for a meaningful chart, but not the raw rows.
        trends = trends[:500]

        if "trend_list" not in locals():
            trend_list = []

        trend_list.append({
            "numeric_column": num,
            "frequency": label,
            "direction": direction,
            "series": trends,
        })

    return {
        "available": bool(locals().get("trend_list")),
        "date_column": date_col,
        "frequency": label,
        "trends": locals().get("trend_list", []),
    }


def key_findings(df, profile, corr, outl, trends, comparisons):
    findings = [
        {
            "id": 1,
            "text": (
                f"The dataset contains {profile['rows']:,} records "
                f"across {profile['columns']} columns."
            ),
        }
    ]

    if profile["missing_pct"] > 0:
        findings.append({
            "id": 2,
            "text": (
                f"Missing values affect {profile['missing_pct']}% "
                "of all dataset cells."
            ),
        })

    if corr.get("strongest"):
        s = corr["strongest"]
        findings.append({
            "id": 3,
            "text": (
                f"{s['a']} and {s['b']} have a {s['strength']} "
                f"Pearson correlation (r={s['correlation']})."
            ),
        })

    if outl["total_outliers"] > 0:
        top = outl["columns"][0] if outl["columns"] else None
        text = f"{outl['total_outliers']:,} outlier values were detected"
        if top:
            text += f", with {top['count']:,} in {top['column']}"
        findings.append({
            "id": 4,
            "text": text + ".",
        })

    if comparisons and comparisons[0]["data"]:
        c = comparisons[0]
        top = c["data"][0]
        findings.append({
            "id": 5,
            "text": (
                f"{top['category']} has the highest average "
                f"{c['numeric_column']} ({top['mean']}) among "
                f"{c['category_column']} groups."
            ),
        })

    if trends.get("available") and trends.get("trends"):
        t = trends["trends"][0]
        findings.append({
            "id": 6,
            "text": (
                f"{t['numeric_column']} shows an {t['direction']} "
                f"trend at {t['frequency']} frequency."
            ),
        })

    return findings[:6]


def build_summary(df, profile, corr, comparisons):
    parts = [
        (
            f"The dataset contains {profile['rows']:,} records across "
            f"{profile['columns']} columns, with "
            f"{len(profile['numeric_columns'])} numeric, "
            f"{len(profile['categorical_columns'])} categorical, and "
            f"{len(profile['datetime_columns'])} date/time features."
        )
    ]

    if profile["missing_pct"] > 0:
        parts.append(
            f"Missing values account for {profile['missing_pct']}% of cells."
        )

    if profile["duplicate_rows"] > 0:
        parts.append(
            f"There are {profile['duplicate_rows']:,} duplicate rows."
        )

    if corr.get("strongest"):
        s = corr["strongest"]
        parts.append(
            f"{s['a']} and {s['b']} have the strongest observed "
            f"relationship (r={s['correlation']})."
        )

    if comparisons:
        parts.append(
            f"{len(comparisons)} useful category-to-numeric comparisons "
            "were identified."
        )

    return " ".join(parts)
