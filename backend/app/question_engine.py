"""Deterministic natural-language question engine.

This module intentionally uses no LLM. It maps common analytical language to
exact Pandas computations and returns chart-ready data.
"""
from __future__ import annotations

import gc
import re

import pandas as pd

from app import visualization_engine as ve


def _normalize(text: str) -> str:
    return re.sub(
        r"[^a-z0-9_%.\- ]+",
        " ",
        str(text).lower(),
    ).strip()


def _tokens(text: str) -> set[str]:
    return set(
        _normalize(text).split()
    )


def _find_column(
    question: str,
    columns: list[str],
) -> str | None:
    q = _normalize(question)

    # Exact phrase first.
    for col in sorted(
        columns,
        key=len,
        reverse=True,
    ):
        c = _normalize(col)

        if c and c in q:
            return col

    # Token overlap.
    q_tokens = _tokens(question)

    best = None
    best_score = 0.0

    for col in columns:

        c_tokens = _tokens(col)

        if not c_tokens:
            continue

        overlap = len(
            q_tokens & c_tokens
        )

        score = (
            overlap / len(c_tokens)
        )

        if (
            overlap
            and score > best_score
        ):
            best = col
            best_score = score

    return best


def _find_category(
    question,
    categorical,
):
    return _find_column(
        question,
        categorical,
    )


def _find_numeric(
    question,
    numeric,
):
    return _find_column(
        question,
        numeric,
    )


def _number(value):
    try:
        return round(
            float(value),
            4,
        )
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

        return (
            f"{n:,.4f}"
            .rstrip("0")
            .rstrip(".")
        )

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
        return _help(
            "Please enter a data-analysis question."
        )

    # =========================================================
    # DATASET OVERVIEW
    # =========================================================

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
        return {
            "intent": "overview",
            "answer": (
                f"The dataset contains "
                f"{profile['rows']:,} records and "
                f"{profile['columns']} columns."
            ),
            "data": profile,
            "visualizations": [],
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # MISSING / NULL
    # =========================================================

    if any(
        word in tokens
        for word in {
            "missing",
            "null",
            "nan",
            "empty",
        }
    ):
        details = [
            c
            for c in profile[
                "column_details"
            ]
            if c["null_count"] > 0
        ]

        details.sort(
            key=lambda x: x["null_count"],
            reverse=True,
        )

        if details:

            top = details[0]

            answer = (
                f"The dataset has "
                f"{profile['missing_values']:,} "
                f"missing values "
                f"({profile['missing_pct']}% "
                "of all cells). "
                f"{top['name']} has the most "
                f"missing values "
                f"({top['null_count']:,}, "
                f"{top['null_pct']}%)."
            )

        else:
            answer = (
                "The dataset contains no "
                "missing values."
            )

        return {
            "intent": "missing",
            "answer": answer,
            "data": {
                "missing_values": profile[
                    "missing_values"
                ],
                "missing_pct": profile[
                    "missing_pct"
                ],
                "columns": details,
            },
            "visualizations": [],
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # DUPLICATES
    # =========================================================

    if (
        "duplicate" in tokens
        or "duplicates" in tokens
    ):
        count = profile[
            "duplicate_rows"
        ]

        return {
            "intent": "duplicates",
            "answer": (
                f"The dataset contains "
                f"{count:,} duplicate rows."
            ),
            "data": {
                "duplicate_rows": count
            },
            "visualizations": [],
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # CORRELATIONS
    # =========================================================

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
                "At least two varying numerical "
                "columns are required for "
                "correlation analysis."
            )

        strongest = corr.get(
            "strongest"
        )

        if strongest:
            answer = (
                f"The strongest correlation is "
                f"between {strongest['a']} and "
                f"{strongest['b']} "
                f"(r={strongest['correlation']}, "
                f"{strongest['strength']})."
            )
        else:
            answer = (
                "No valid numerical "
                "correlations were found."
            )

        return {
            "intent": "correlations",
            "answer": answer,
            "data": {
                "pairs": corr[
                    "pairs"
                ][:15],
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
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # OUTLIERS
    # =========================================================

    if (
        "outlier" in tokens
        or "outliers" in tokens
    ):
        target = _find_numeric(
            question,
            numeric,
        )

        if target:

            item = next(
                (
                    x
                    for x in outl[
                        "columns"
                    ]
                    if x["column"] == target
                ),
                None,
            )

            if item:
                answer = (
                    f"{target} contains "
                    f"{item['count']:,} outliers "
                    f"({item['pct']}% of valid values)."
                )
            else:
                answer = (
                    f"No outlier result is "
                    f"available for {target}."
                )

        else:

            top = (
                outl["columns"][0]
                if outl["columns"]
                else None
            )

            if top:
                answer = (
                    f"{outl['total_outliers']:,} "
                    f"outlier values were detected. "
                    f"{top['column']} has the most "
                    f"({top['count']:,})."
                )
            else:
                answer = (
                    "No numerical columns are "
                    "available for outlier detection."
                )

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
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # TREND
    # =========================================================

    if (
        any(
            word in tokens
            for word in {
                "trend",
                "trends",
                "growth",
            }
        )
        or "over time" in q
        or "time series" in q
    ):
        if not trends.get(
            "available"
        ):
            return _help(
                "No usable date/time column "
                "was detected for trend analysis."
            )

        target = _find_numeric(
            question,
            numeric,
        )

        selected = None

        if target:
            selected = next(
                (
                    t
                    for t in trends.get(
                        "trends",
                        [],
                    )
                    if t[
                        "numeric_column"
                    ] == target
                ),
                None,
            )

        if (
            selected is None
            and trends.get("trends")
        ):
            selected = trends[
                "trends"
            ][0]

        if selected:
            answer = (
                f"{selected['numeric_column']} "
                f"shows an "
                f"{selected['direction']} trend "
                f"at {selected['frequency']} "
                "frequency."
            )
        else:
            answer = (
                "No usable trend series "
                "was found."
            )

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
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # DISTRIBUTION
    # =========================================================

    if (
        "distribution" in q
        or "histogram" in q
        or "spread of" in q
    ):
        target = _find_numeric(
            question,
            numeric,
        )

        if not target:
            return _help(
                "Please specify a "
                "numerical column."
            )

        # Numeric columns have already been
        # normalized by profiler.py.
        s = df[target]

        if not pd.api.types.is_numeric_dtype(
            s
        ):
            s = pd.to_numeric(
                s,
                errors="coerce",
            )

        valid_count = int(
            s.notna().sum()
        )

        if valid_count == 0:
            return _help(
                f"{target} does not contain "
                "usable numerical values."
            )

        mean = s.mean()
        median = s.median()
        std = s.std()
        minimum = s.min()
        maximum = s.max()

        result = {
            "intent": "distribution",
            "answer": (
                f"{target} has a mean of "
                f"{_format(mean)}, median of "
                f"{_format(median)}, and "
                f"standard deviation of "
                f"{_format(std)}."
            ),
            "data": {
                "column": target,
                "mean": _number(mean),
                "median": _number(median),
                "std": _number(std),
                "min": _number(minimum),
                "max": _number(maximum),
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
            "suggestions": _help()[
                "suggestions"
            ],
        }

        return result

    # =========================================================
    # COUNT BY CATEGORY
    # =========================================================

    count_request = (
        "count" in tokens
        or "number of" in q
        or "how many" in q
    )

    if count_request:

        cat = _find_category(
            question,
            categorical,
        )

        if cat:

            counts = (
                df[cat]
                .value_counts(
                    dropna=True
                )
                .head(20)
            )

            data = [
                {
                    "category": str(k),
                    "value": int(v),
                }
                for k, v in counts.items()
            ]

            if data:
                answer = (
                    f"{data[0]['category']} "
                    f"has the highest count "
                    f"with {data[0]['value']:,} records."
                )
            else:
                answer = (
                    f"There are "
                    f"{len(df):,} records."
                )

            return {
                "intent": "count",
                "answer": answer,
                "data": data,
                "visualizations": [{
                    "type": "bar",
                    "title": f"Count by {cat}",
                    "x_label": cat,
                    "y_label": "Count",
                    "data": data,
                }],
                "suggestions": _help()[
                    "suggestions"
                ],
            }

        return {
            "intent": "count",
            "answer": (
                f"The dataset contains "
                f"{len(df):,} records."
            ),
            "data": {
                "count": int(len(df))
            },
            "visualizations": [],
            "suggestions": _help()[
                "suggestions"
            ],
        }

    # =========================================================
    # AGGREGATIONS
    # =========================================================

    operation = None

    if (
        "average" in q
        or "mean" in tokens
        or "avg" in tokens
    ):
        operation = "average"

    elif "median" in tokens:
        operation = "median"

    elif any(
        x in tokens
        for x in {
            "sum",
            "total",
        }
    ):
        operation = "sum"

    elif any(
        x in tokens
        for x in {
            "minimum",
            "min",
        }
    ):
        operation = "minimum"

    elif any(
        x in tokens
        for x in {
            "maximum",
            "max",
        }
    ):
        operation = "maximum"

    if operation:

        num = _find_numeric(
            question,
            numeric,
        )

        cat = _find_category(
            question,
            categorical,
        )

        # -----------------------------------------------------
        # Category + numeric
        # -----------------------------------------------------

        if cat and num:

            # Avoid creating a temporary 50K-row DataFrame.
            try:
                grouped = (
                    df.groupby(
                        cat,
                        dropna=True,
                        observed=True,
                    )[num]
                )

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

                values = (
                    values
                    .sort_values(
                        ascending=False
                    )
                    .head(20)
                )

            except Exception:
                return _help(
                    f"Unable to calculate "
                    f"{operation} for {num}."
                )

            if values.empty:
                return _help(
                    f"No valid values were "
                    f"found for {num}."
                )

            data = [
                {
                    "category": str(k),
                    "value": _number(v),
                }
                for k, v in values.items()
            ]

            top = (
                data[0]
                if data
                else None
            )

            label = {
                "average": "average",
                "median": "median",
                "sum": "total",
                "minimum": "minimum",
                "maximum": "maximum",
            }[operation]

            answer = (
                f"{top['category']} has the "
                f"highest {label} {num}: "
                f"{_format(top['value'])}."
                if top
                else
                f"No grouped {label} "
                "result was available."
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
                    "title": (
                        f"{label.title()} "
                        f"{num} by {cat}"
                    ),
                    "x_label": cat,
                    "y_label": (
                        f"{label.title()} {num}"
                    ),
                    "data": data,
                }],
                "suggestions": _help()[
                    "suggestions"
                ],
            }

        # -----------------------------------------------------
        # Overall numeric aggregation
        # -----------------------------------------------------

        if num:

            s = df[num]

            if not pd.api.types.is_numeric_dtype(
                s
            ):
                s = pd.to_numeric(
                    s,
                    errors="coerce",
                )

            if int(s.notna().sum()) == 0:
                return _help(
                    f"No valid numerical "
                    f"values were found in {num}."
                )

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
                    f"The {label} of {num} "
                    f"is {_format(value)}."
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
                "suggestions": _help()[
                    "suggestions"
                ],
            }

    # =========================================================
    # HIGHEST / LOWEST / COMPARISON
    # =========================================================

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

        cat = _find_category(
            question,
            categorical,
        )

        num = _find_numeric(
            question,
            numeric,
        )

        selected = None

        for comparison in comparisons:

            if (
                cat
                and comparison[
                    "category_column"
                ] != cat
            ):
                continue

            if (
                num
                and comparison[
                    "numeric_column"
                ] != num
            ):
                continue

            selected = comparison
            break

        if selected is None and comparisons:
            selected = comparisons[0]

        if (
            selected
            and selected["data"]
        ):

            descending = (
                "lowest" not in q
                and "worst" not in q
            )

            rows = sorted(
                selected["data"],
                key=lambda x: (
                    x["mean"] is not None,
                    x["mean"] or 0,
                ),
                reverse=descending,
            )

            top = rows[0]

            direction = (
                "highest"
                if descending
                else "lowest"
            )

            chart_data = [
                {
                    "category": row[
                        "category"
                    ],
                    "value": row[
                        "mean"
                    ],
                }
                for row in rows
                if row["mean"] is not None
            ]

            return {
                "intent": "comparison",
                "answer": (
                    f"{top['category']} has the "
                    f"{direction} average "
                    f"{selected['numeric_column']} "
                    f"at {_format(top['mean'])}."
                ),
                "data": selected,
                "visualizations": [{
                    "type": "bar",
                    "title": (
                        f"Average "
                        f"{selected['numeric_column']} "
                        f"by "
                        f"{selected['category_column']}"
                    ),
                    "x_label": selected[
                        "category_column"
                    ],
                    "y_label": (
                        f"Average "
                        f"{selected['numeric_column']}"
                    ),
                    "data": chart_data[:20],
                }],
                "suggestions": _help()[
                    "suggestions"
                ],
            }

    gc.collect()

    return _help()


def make_suggestions(profile):
    numeric = profile[
        "numeric_columns"
    ]

    categorical = profile[
        "categorical_columns"
    ]

    datetime = profile[
        "datetime_columns"
    ]

    suggestions = []

    if numeric:
        suggestions.append(
            f"What is the average of {numeric[0]}?"
        )

    if categorical and numeric:
        suggestions.append(
            f"Which {categorical[0]} has the "
            f"highest average {numeric[0]}?"
        )

    if len(numeric) >= 2:
        suggestions.append(
            "Which numerical features are "
            "strongly correlated?"
        )

    if datetime and numeric:
        suggestions.append(
            f"Show the trend of "
            f"{numeric[0]} over time."
        )

    suggestions.append(
        "Find outliers."
    )

    return suggestions[:5]