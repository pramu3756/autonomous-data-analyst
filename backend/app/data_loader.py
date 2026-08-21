"""Dataset loading and caching for DataPilot."""
from __future__ import annotations

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
        raise ValueError("Unsupported file format. Please upload a CSV, XLSX, or XLS file.")

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


def _load_dataframe(dataset_id: str) -> pd.DataFrame:
    meta = _DATASETS.get(dataset_id)
    if meta is None:
        raise KeyError("Dataset not found. Please upload the file again.")

    if meta["df"] is not None:
        return meta["df"]

    path: Path = meta["path"]
    ext = path.suffix.lower()

    try:
        if ext == ".csv":
            df = pd.read_csv(
                path,
                low_memory=False,
                encoding_errors="replace",
            )
        elif ext == ".xlsx":
            df = pd.read_excel(path, engine="openpyxl")
        else:
            # Legacy .xls requires xlrd.
            df = pd.read_excel(path, engine="xlrd")
    except Exception as exc:
        raise ValueError(
            f"Unable to read this {ext.lstrip('.').upper()} file: {exc}"
        ) from exc

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    # Normalize column names once.
    original = [str(c) for c in df.columns]
    clean = []
    seen: dict[str, int] = {}
    for name in original:
        name = name.strip() or "Unnamed"
        count = seen.get(name, 0)
        seen[name] = count + 1
        clean.append(name if count == 0 else f"{name}_{count + 1}")
    df.columns = clean

    meta["df"] = df
    return df


def get_dataset(dataset_id: str) -> dict:
    if dataset_id not in _DATASETS:
        raise KeyError("Dataset not found. Please upload the file again.")
    return _DATASETS[dataset_id]


def get_df(dataset_id: str) -> pd.DataFrame:
    return _load_dataframe(dataset_id)


def cleanup_dataset(dataset_id: str) -> None:
    meta = _DATASETS.pop(dataset_id, None)
    if meta and meta.get("path"):
        try:
            Path(meta["path"]).unlink(missing_ok=True)
        except OSError:
            pass
