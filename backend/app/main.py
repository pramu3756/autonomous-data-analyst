"""DataPilot — Autonomous Data Analyst API."""
from __future__ import annotations


import gc
import math
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import (
    analysis_engine as ae,
    data_loader,
    profiler,
    quality_engine,
    question_engine as qe,
    visualization_engine as ve,
)

MAX_FILE_SIZE = (
    int(os.environ.get("DATAPILOT_MAX_FILE_SIZE_MB", "100"))
    * 1024
    * 1024
)

app = FastAPI(
    title="DataPilot — Autonomous Data Analyst",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_profile(dataset_id: str) -> dict:
    meta = data_loader.get_dataset(dataset_id)

    if meta.get("profile") is not None:
        return meta["profile"]

    df = data_loader.get_df(dataset_id)

    profile = profiler.build_profile(
        df,
        meta["name"],
        meta["size"],
    )

    meta["profile"] = profile
    return profile


def _ensure_analysis(dataset_id: str) -> dict:
    meta = data_loader.get_dataset(dataset_id)

    if meta.get("analysis") is not None:
        return meta["analysis"]

    df = data_loader.get_df(dataset_id)
    profile = _ensure_profile(dataset_id)

    numeric = profile["numeric_columns"]
    categorical = profile["categorical_columns"]
    datetime = profile["datetime_columns"]

    corr = ae.correlations(df, numeric)
    outl = ae.outliers(df, numeric)
    comparisons = ae.group_comparisons(
        df,
        numeric,
        categorical,
    )
    trends = ae.trend_analysis(
        df,
        numeric,
        datetime,
    )

    result = {
        "summary": ae.build_summary(
            df,
            profile,
            corr,
            comparisons,
        ),
        "numeric_stats": ae.numeric_stats(
            df,
            numeric,
        ),
        "correlations": corr,
        "outliers": outl,
        "group_comparisons": comparisons,
        "trends": trends,
        "key_findings": ae.key_findings(
            df,
            profile,
            corr,
            outl,
            trends,
            comparisons,
        ),
    }

    meta["analysis"] = result
    meta["correlations"] = corr
    meta["outliers"] = outl

    return result


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "DataPilot Autonomous Data Analyst",
        "engine": "deterministic",
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided.",
        )

    ext = Path(file.filename).suffix.lower()

    if ext not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported file format. "
                "Please upload a CSV, XLSX, or XLS file."
            ),
        )

    dataset_id = None
    temp_path = None

    try:
        # ---------------------------------------------------------
        # Stream upload to disk instead of loading the complete
        # file into RAM.
        # ---------------------------------------------------------

        dataset_id = os.urandom(8).hex()

        temp_path = (
            Path(
                tempfile.gettempdir()
            )
            / f"datapilot_{dataset_id}{ext}"
        )

        total_size = 0
        chunk_size = 1024 * 1024  # 1 MB

        with temp_path.open("wb") as output:

            while True:
                chunk = await file.read(
                    chunk_size
                )

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    output.close()

                    try:
                        temp_path.unlink(
                            missing_ok=True
                        )
                    except OSError:
                        pass

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File exceeds the maximum "
                            f"size of "
                            f"{MAX_FILE_SIZE // (1024 * 1024)} MB."
                        ),
                    )

                output.write(chunk)

        # ---------------------------------------------------------
        # Register the file with the dataset loader.
        # ---------------------------------------------------------

        meta = {
            "path": temp_path,
            "name": file.filename,
            "size": total_size,
            "df": None,
            "profile": None,
            "correlations": None,
            "outliers": None,
            "charts": None,
            "analysis": None,
        }

        data_loader._DATASETS[dataset_id] = meta

        # ---------------------------------------------------------
        # Build profile.
        # ---------------------------------------------------------

        profile = _ensure_profile(
            dataset_id
        )

        # Release upload-related temporary memory.
        gc.collect()

        return {
            "dataset_id": dataset_id,
            "message": (
                "Dataset successfully processed "
                "and ready for deterministic analysis."
            ),
            "profile": profile,
        }

    except HTTPException:
        raise

    except ValueError as exc:

        if dataset_id:
            data_loader.cleanup_dataset(
                dataset_id
            )

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        if dataset_id:
            data_loader.cleanup_dataset(
                dataset_id
            )
        elif temp_path:
            try:
                temp_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        ) from exc

    finally:
        try:
            await file.close()
        except Exception:
            pass
@app.get("/dataset/{dataset_id}/profile")
def get_profile(dataset_id: str):
    try:
        return _ensure_profile(dataset_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


def _json_value(value):
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, float) and math.isnan(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def _df_to_records(df):
    records = []

    for row in df.itertuples(
        index=False,
        name=None,
    ):
        records.append({
            str(column): _json_value(value)
            for column, value in zip(
                df.columns,
                row,
            )
        })

    return records


@app.get("/dataset/{dataset_id}/preview")
def get_preview(
    dataset_id: str,
    page: int = Query(
        1,
        ge=1,
    ),
    page_size: int = Query(
        100,
        ge=1,
        le=500,
    ),
):
    try:
        df = data_loader.get_df(dataset_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    total = len(df)
    total_pages = max(
        1,
        (total + page_size - 1) // page_size,
    )

    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    chunk = df.iloc[
        start:start + page_size
    ]

    return {
        "page": page,
        "page_size": page_size,
        "total_rows": total,
        "total_pages": total_pages,
        "columns": list(df.columns),
        "rows": _df_to_records(chunk),
    }


@app.post("/dataset/{dataset_id}/analyze")
def analyze(dataset_id: str):
    try:
        return _ensure_analysis(dataset_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {exc}",
        ) from exc


@app.get("/dataset/{dataset_id}/charts")
def get_charts(dataset_id: str):
    try:
        df = data_loader.get_df(dataset_id)
        profile = _ensure_profile(dataset_id)
        analysis = _ensure_analysis(dataset_id)

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    meta = data_loader.get_dataset(dataset_id)

    if meta.get("charts") is None:
        meta["charts"] = ve.generate_charts(
            df,
            profile,
            analysis["correlations"],
        )

    return {
        "charts": meta["charts"],
    }


@app.get("/dataset/{dataset_id}/quality")
def get_quality(dataset_id: str):
    try:
        df = data_loader.get_df(dataset_id)
        profile = _ensure_profile(dataset_id)
        return quality_engine.compute_quality(
            df,
            profile,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.get("/dataset/{dataset_id}/correlations")
def get_correlations(dataset_id: str):
    try:
        analysis = _ensure_analysis(dataset_id)
        return analysis["correlations"]
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.get("/dataset/{dataset_id}/outliers")
def get_outliers(dataset_id: str):
    try:
        analysis = _ensure_analysis(dataset_id)
        return analysis["outliers"]
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


class QuestionBody(BaseModel):
    question: str


@app.post("/dataset/{dataset_id}/question")
def ask_question(
    dataset_id: str,
    body: QuestionBody,
):
    question = (body.question or "").strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question.",
        )

    try:
        df = data_loader.get_df(dataset_id)
        profile = _ensure_profile(dataset_id)
        analysis = _ensure_analysis(dataset_id)

        result = qe.answer_question(
            question,
            df,
            profile,
            analysis["correlations"],
            analysis["outliers"],
            analysis["trends"],
            analysis["group_comparisons"],
        )

        result["question"] = question
        result["ai_mode"] = "deterministic"

        return result

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Question analysis failed: {exc}",
        ) from exc
