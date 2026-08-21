"""Dataset loading and caching for DataPilot."""
from __future__ import annotations

import gc
import tempfile
import uuid
from pathlib import Path

import pandas as pd

UPLOAD_DIR = Path(tempfile.gettempdir()) / "datapilot_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_DATASETS: dict[str, dict] = {}


def save_upload(file_name: str, file_bytes: bytes) -> str:
    dataset_id = uuid.uuid4().hex[:12]
    ext = Path(file_name).suffix.lower()

    if ext not in {".csv", ".xlsx", ".xls"}:
        raise ValueError(
            "Unsupported file format. Please upload a CSV, XLSX, or XLS file."
        )

    dest = UPLOAD_DIR / f"{dataset_id}{ext}"
    dest.write_bytes(file_bytes)

    _DATASETS[dataset_id] = {
        "path": dest,
        "name": file_name,
        "size": len(file_bytes),
        "df": None,
        "profile": None,
        "correlations": None,
        "outliers": None,
        "charts": None,
        "analysis": None,
    }

    return dataset_id


def _optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce memory usage without changing the logical values
    or converting arbitrary text columns to categorical data.
    """

    for column in df.columns:
        dtype = df[column].dtype

        # Downcast integer columns.
        if pd.api.types.is_integer_dtype(dtype):
            df[column] = pd.to_numeric(
                df[column],
                downcast="integer",
            )

        # Downcast floating-point columns.
        elif pd.api.types.is_float_dtype(dtype):
            df[column] = pd.to_numeric(
                df[column],
                downcast="float",
            )

    return df


def _load_dataframe(dataset_id: str) -> pd.DataFrame:
    meta = _DATASETS.get(dataset_id)

    if meta is None:
        raise KeyError(
            "Dataset not found. Please upload the file again."
        )

    # Return cached DataFrame if already loaded.
    if meta["df"] is not None:
        return meta["df"]

    path: Path = meta["path"]
    ext = path.suffix.lower()

    try:
        if ext == ".csv":
            df = pd.read_csv(
                path,
                low_memory=True,
                encoding_errors="replace",
                memory_map=True,
            )

        elif ext == ".xlsx":
            df = pd.read_excel(
                path,
                engine="openpyxl",
            )

        else:
            # Legacy .xls requires xlrd.
            df = pd.read_excel(
                path,
                engine="xlrd",
            )

    except Exception as exc:
        raise ValueError(
            f"Unable to read this {ext.lstrip('.').upper()} file: {exc}"
        ) from exc

    if df.empty:
        del df
        gc.collect()
        raise ValueError("The uploaded dataset is empty.")

    # Normalize column names once.
    original = [str(c) for c in df.columns]

    clean: list[str] = []
    seen: dict[str, int] = {}

    for name in original:
        name = name.strip() or "Unnamed"

        count = seen.get(name, 0)
        seen[name] = count + 1

        clean.append(
            name if count == 0 else f"{name}_{count + 1}"
        )

    df.columns = clean

    # Reduce numeric memory usage.
    df = _optimize_dataframe_memory(df)

    # Store the single DataFrame instance.
    meta["df"] = df

    return df


def get_dataset(dataset_id: str) -> dict:
    if dataset_id not in _DATASETS:
        raise KeyError(
            "Dataset not found. Please upload the file again."
        )

    return _DATASETS[dataset_id]


def get_df(dataset_id: str) -> pd.DataFrame:
    return _load_dataframe(dataset_id)

def register_upload(
    dataset_id: str,
    file_name: str,
    path: Path,
    size: int,
) -> str:
    ext = Path(file_name).suffix.lower()

    if ext not in {".csv", ".xlsx", ".xls"}:
        raise ValueError(
            "Unsupported file format. "
            "Please upload a CSV, XLSX, or XLS file."
        )

    _DATASETS[dataset_id] = {
        "path": path,
        "name": file_name,
        "size": size,
        "df": None,
        "profile": None,
        "correlations": None,
        "outliers": None,
        "charts": None,
        "analysis": None,
    }

    return dataset_id

def cleanup_dataset(dataset_id: str) -> None:
    meta = _DATASETS.pop(dataset_id, None)

    if meta is None:
        return

    # Release DataFrame from memory.
    meta["df"] = None
    meta["profile"] = None
    meta["correlations"] = None
    meta["outliers"] = None
    meta["charts"] = None
    meta["analysis"] = None

    gc.collect()

    # Delete uploaded file.
    if meta.get("path"):
        try:
            Path(meta["path"]).unlink(missing_ok=True)
        except OSError:
            pass