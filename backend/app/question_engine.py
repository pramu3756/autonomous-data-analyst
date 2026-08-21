"""Deterministic natural-language question engine.

This module intentionally uses no LLM. It maps common analytical language to
exact Pandas computations and returns chart-ready data.
"""
from __future__ import annotations

import re
import pandas as pd

from app import visualization_engine as ve


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9_%.\- ]+", " ", str(text).lower()).strip()


def _tokens(text: str) -> set[str]:
    return set(_normalize(text).split())


def _find_column(question: str, columns: list[str]) -> str | None:
    q = _normalize(question)

    # Exact phrase first.
    for col in sorted(columns, key=len, reverse=True):
        c = _normalize(col)
        if c and c in q:
            return col

    # Token overlap for columns like "Monthly Charges".
    q_tokens = _tokens(question)
    best = None
    best_score = 0.0

    for col in columns:
        c_tokens = _tokens(col)
        if not c_tokens:
            continue
        overlap = len(q_tokens & c_tokens)
        score = overlap / len(c_tokens)
        if overlap and score > best_score:
            best = col
            best_score = score

    return best


def _find_category(question, categorical):
    return _find_column(question, categorical)


def _find_numeric(question, numeric):
    return _find_column(question, numeric)


def _number(value):
    try:
        return round(float(value), 4)
    except Exception:
        return None


def _format(value):
    if value is None:
        return "N/A"
    if isinstance(value, int):
        return f"{value:,}"
    try:
        n = float(value)
        if n.is_integer():
            return f"{int(n):,}"
        return f"{n:,.4f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _help(extra=None):
    return {
        "intent": "unknown",
        "answer": extra or (
            "I could not map that question to a supported analysis. "
            "Try asking about averages, totals, highest/lowest values, "
            "categories, trends, correlations, distributions, missing values, "
            "duplicates, or outliers."
        ),
        "data": None,
        "visualizations": [],
        "suggestions": [
            "Which category has the highest average value?",
            "Which numerical features are strongly correlated?",
            "Show the trend over time.",
            "Find outliers.",
            "What is the average of MonthlyCharges?",
            "How many records are in each category?",
        ],
    }


def answer_question(
    question,
    df,
    profile,
    corr,
    outl,
    trends,
    comparisons,
):
    q = _normalize(question)
    tokens = _tokens(question)

    numeric = profile["numeric_columns"]
    categorical = profile["categorical_columns"]
    datetime = profile["datetime_columns"]

    if not q:
        return _help("Please enter a data-analysis question.")

    # ---------------------------------------------------------
    # Dataset overview
    # ---------------------------------------------------------
    if any(
        phrase in q
        for phrase in [
            "dataset overview",
            "overview of dataset",
            "how many rows",
            "how many records",
            "number of rows",
            "number of records",
        ]
    ):
        answer = (
            f"The dataset contains {profile['rows']:,} records and "
            f"{profile['columns']} columns."
        )
        return {
            "intent": "overview",
            "answer": answer,
            "data": profile,
            "visualizations": [],
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Missing / null
    # ---------------------------------------------------------
    if any(
        word in tokens
        for word in {"missing", "null", "nan", "empty"}
    ):
        details = [
            c for c in profile["column_details"]
            if c["null_count"] > 0
        ]
        details.sort(
            key=lambda x: x["null_count"],
            reverse=True,
        )

        if details:
            top = details[0]
            answer = (
                f"The dataset has {profile['missing_values']:,} missing values "
                f"({profile['missing_pct']}% of all cells). "
                f"{top['name']} has the most missing values "
                f"({top['null_count']:,}, {top['null_pct']}%)."
            )
        else:
            answer = "The dataset contains no missing values."

        return {
            "intent": "missing",
            "answer": answer,
            "data": {
                "missing_values": profile["missing_values"],
                "missing_pct": profile["missing_pct"],
                "columns": details,
            },
            "visualizations": [],
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Duplicate rows
    # ---------------------------------------------------------
    if "duplicate" in tokens or "duplicates" in tokens:
        count = profile["duplicate_rows"]
        return {
            "intent": "duplicates",
            "answer": f"The dataset contains {count:,} duplicate rows.",
            "data": {"duplicate_rows": count},
            "visualizations": [],
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Correlations
    # ---------------------------------------------------------
    if any(
        word in q
        for word in [
            "correlation",
            "correlated",
            "relationship between",
            "relationships between",
            "strongly related",
            "strong relationship",
        ]
    ):
        if not corr.get("available"):
            return _help(
                "At least two varying numerical columns are required "
                "for correlation analysis."
            )

        strongest = corr.get("strongest")
        if strongest:
            answer = (
                f"The strongest correlation is between "
                f"{strongest['a']} and {strongest['b']} "
                f"(r={strongest['correlation']}, "
                f"{strongest['strength']})."
            )
        else:
            answer = "No valid numerical correlations were found."

        return {
            "intent": "correlations",
            "answer": answer,
            "data": {
                "pairs": corr["pairs"][:15],
                "strongest": strongest,
            },
            "visualizations": ve.chart_for_question(
                question,
                df,
                profile,
                corr,
                outl,
                trends,
                comparisons,
                "correlations",
            ),
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Outliers
    # ---------------------------------------------------------
    if "outlier" in tokens or "outliers" in tokens:
        target = _find_numeric(question, numeric)
        if target:
            item = next(
                (
                    x for x in outl["columns"]
                    if x["column"] == target
                ),
                None,
            )
            if item:
                answer = (
                    f"{target} contains {item['count']:,} outliers "
                    f"({item['pct']}% of valid values)."
                )
            else:
                answer = f"No outlier result is available for {target}."
        else:
            top = outl["columns"][0] if outl["columns"] else None
            if top:
                answer = (
                    f"{outl['total_outliers']:,} outlier values were detected. "
                    f"{top['column']} has the most ({top['count']:,})."
                )
            else:
                answer = "No numerical columns are available for outlier detection."

        return {
            "intent": "outliers",
            "answer": answer,
            "data": outl,
            "visualizations": ve.chart_for_question(
                question,
                df,
                profile,
                corr,
                outl,
                trends,
                comparisons,
                "outliers",
                column=target,
            ),
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Trend / time series
    # ---------------------------------------------------------
    if (
        any(word in tokens for word in {"trend", "trends", "growth"})
        or "over time" in q
        or "time series" in q
    ):
        if not trends.get("available"):
            return _help(
                "No usable date/time column was detected for trend analysis."
            )

        target = _find_numeric(question, numeric)
        selected = None

        if target:
            selected = next(
                (
                    t for t in trends.get("trends", [])
                    if t["numeric_column"] == target
                ),
                None,
            )

        if selected is None and trends.get("trends"):
            selected = trends["trends"][0]

        if selected:
            answer = (
                f"{selected['numeric_column']} shows an "
                f"{selected['direction']} trend at "
                f"{selected['frequency']} frequency."
            )
        else:
            answer = "No usable trend series was found."

        return {
            "intent": "trends",
            "answer": answer,
            "data": selected,
            "visualizations": ve.chart_for_question(
                question,
                df,
                profile,
                corr,
                outl,
                trends,
                comparisons,
                "trends",
                column=target,
            ),
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Distribution
    # ---------------------------------------------------------
    if (
        "distribution" in q
        or "histogram" in q
        or "spread of" in q
    ):
        target = _find_numeric(question, numeric)
        if not target:
            return _help("Please specify a numerical column.")

        s = pd.to_numeric(df[target], errors="coerce").dropna()

        if s.empty:
            return _help(f"{target} does not contain usable numerical values.")

        return {
            "intent": "distribution",
            "answer": (
                f"{target} has a mean of {_format(s.mean())}, "
                f"median of {_format(s.median())}, and "
                f"standard deviation of {_format(s.std())}."
            ),
            "data": {
                "column": target,
                "mean": _number(s.mean()),
                "median": _number(s.median()),
                "std": _number(s.std()),
                "min": _number(s.min()),
                "max": _number(s.max()),
            },
            "visualizations": ve.chart_for_question(
                question,
                df,
                profile,
                corr,
                outl,
                trends,
                comparisons,
                "distribution",
                column=target,
            ),
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Count by category
    # ---------------------------------------------------------
    count_request = (
        "count" in tokens
        or "number of" in q
        or "how many" in q
    )

    if count_request:
        cat = _find_category(question, categorical)

        if cat:
            counts = (
                df[cat]
                .value_counts(dropna=True)
                .head(20)
            )

            data = [
                {
                    "category": str(k),
                    "value": int(v),
                }
                for k, v in counts.items()
            ]

            return {
                "intent": "count",
                "answer": (
                    f"{data[0]['category']} has the highest count "
                    f"with {data[0]['value']:,} records."
                    if data else
                    f"There are {len(df):,} records."
                ),
                "data": data,
                "visualizations": [{
                    "type": "bar",
                    "title": f"Count by {cat}",
                    "x_label": cat,
                    "y_label": "Count",
                    "data": data,
                }],
                "suggestions": _help()["suggestions"],
            }

        return {
            "intent": "count",
            "answer": f"The dataset contains {len(df):,} records.",
            "data": {"count": int(len(df))},
            "visualizations": [],
            "suggestions": _help()["suggestions"],
        }

    # ---------------------------------------------------------
    # Aggregation: average / mean / median / sum / min / max
    # ---------------------------------------------------------
    operation = None

    if "average" in q or "mean" in tokens or "avg" in tokens:
        operation = "average"
    elif "median" in tokens:
        operation = "median"
    elif any(x in tokens for x in {"sum", "total"}):
        operation = "sum"
    elif any(x in tokens for x in {"minimum", "min"}):
        operation = "minimum"
    elif any(x in tokens for x in {"maximum", "max"}):
        operation = "maximum"

    if operation:
        num = _find_numeric(question, numeric)

        # Category + numeric aggregation.
        cat = _find_category(question, categorical)

        if cat and num:
            temp = pd.DataFrame({
                "_cat": df[cat],
                "_value": pd.to_numeric(df[num], errors="coerce"),
            }).dropna()

            if temp.empty:
                return _help(f"No valid values were found for {num}.")

            grouped = temp.groupby("_cat")["_value"]

            if operation == "average":
                values = grouped.mean()
            elif operation == "median":
                values = grouped.median()
            elif operation == "sum":
                values = grouped.sum()
            elif operation == "minimum":
                values = grouped.min()
            else:
                values = grouped.max()

            values = values.sort_values(ascending=False).head(20)

            data = [
                {
                    "category": str(k),
                    "value": _number(v),
                }
                for k, v in values.items()
            ]

            top = data[0] if data else None
            label = {
                "average": "average",
                "median": "median",
                "sum": "total",
                "minimum": "minimum",
                "maximum": "maximum",
            }[operation]

            answer = (
                f"{top['category']} has the highest {label} "
                f"{num}: {_format(top['value'])}."
                if top else
                f"No grouped {label} result was available."
            )

            return {
                "intent": "group_comparison",
                "answer": answer,
                "data": {
                    "category_column": cat,
                    "numeric_column": num,
                    "operation": operation,
                    "rows": data,
                },
                "visualizations": [{
                    "type": "bar",
                    "title": f"{label.title()} {num} by {cat}",
                    "x_label": cat,
                    "y_label": f"{label.title()} {num}",
                    "data": data,
                }],
                "suggestions": _help()["suggestions"],
            }

        # Overall numeric aggregation.
        if num:
            s = pd.to_numeric(df[num], errors="coerce").dropna()

            if s.empty:
                return _help(f"No valid numerical values were found in {num}.")

            if operation == "average":
                value = s.mean()
                label = "average"
            elif operation == "median":
                value = s.median()
                label = "median"
            elif operation == "sum":
                value = s.sum()
                label = "total"
            elif operation == "minimum":
                value = s.min()
                label = "minimum"
            else:
                value = s.max()
                label = "maximum"

            return {
                "intent": operation,
                "answer": (
                    f"The {label} of {num} is {_format(value)}."
                ),
                "data": {
                    "column": num,
                    "value": _number(value),
                },
                "visualizations": ve.chart_for_question(
                    question,
                    df,
                    profile,
                    corr,
                    outl,
                    trends,
                    comparisons,
                    operation,
                    column=num,
                ),
                "suggestions": _help()["suggestions"],
            }

    # ---------------------------------------------------------
    # Highest / lowest / top / compare
    # ---------------------------------------------------------
    if any(
        word in q
        for word in [
            "highest",
            "lowest",
            "top ",
            "best",
            "worst",
            "compare",
            "comparison",
        ]
    ):
        cat = _find_category(question, categorical)
        num = _find_numeric(question, numeric)

        selected = None

        for comparison in comparisons:
            if cat and comparison["category_column"] != cat:
                continue
            if num and comparison["numeric_column"] != num:
                continue
            selected = comparison
            break

        if selected is None and comparisons:
            selected = comparisons[0]

        if selected and selected["data"]:
            descending = "lowest" not in q and "worst" not in q
            rows = sorted(
                selected["data"],
                key=lambda x: (
                    x["mean"] is not None,
                    x["mean"] or 0,
                ),
                reverse=descending,
            )

            top = rows[0]
            direction = "highest" if descending else "lowest"

            chart_data = [
                {
                    "category": row["category"],
                    "value": row["mean"],
                }
                for row in rows
                if row["mean"] is not None
            ]

            return {
                "intent": "comparison",
                "answer": (
                    f"{top['category']} has the {direction} average "
                    f"{selected['numeric_column']} at "
                    f"{_format(top['mean'])}."
                ),
                "data": selected,
                "visualizations": [{
                    "type": "bar",
                    "title": (
                        f"Average {selected['numeric_column']} "
                        f"by {selected['category_column']}"
                    ),
                    "x_label": selected["category_column"],
                    "y_label": f"Average {selected['numeric_column']}",
                    "data": chart_data[:20],
                }],
                "suggestions": _help()["suggestions"],
            }

    return _help()


def make_suggestions(profile):
    numeric = profile["numeric_columns"]
    categorical = profile["categorical_columns"]
    datetime = profile["datetime_columns"]

    suggestions = []

    if numeric:
        suggestions.append(f"What is the average of {numeric[0]}?")
    if categorical and numeric:
        suggestions.append(
            f"Which {categorical[0]} has the highest average {numeric[0]}?"
        )
    if len(numeric) >= 2:
        suggestions.append("Which numerical features are strongly correlated?")
    if datetime and numeric:
        suggestions.append(f"Show the trend of {numeric[0]} over time.")
    suggestions.append("Find outliers.")
    return suggestions[:5]
