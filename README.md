# DataPilot — Autonomous Data Analyst

DataPilot is a full-stack, deterministic data-analysis platform. Upload CSV, XLSX, or legacy XLS datasets and analyze them locally with Python/Pandas — **no Gemini, no LLM, and no external AI API**.

## What was improved

- Supports CSV, XLSX and XLS (`xlrd` for legacy `.xls`)
- Robust numeric-string detection (e.g. `"1889.50"` becomes numeric when appropriate)
- Automatic date/time detection
- Efficient paginated dataset preview
- Cached profiling, correlations, outliers and analysis
- 50,000+ row analysis tested successfully
- Vectorized Pandas/Numpy calculations
- Correlation analysis with bounded heatmap size
- IQR outlier detection
- Automatic category/numeric group comparisons
- Automatic trend detection
- Automatic relevant chart selection
- Proper pie, scatter, histogram, line, bar, heatmap and SVG boxplot rendering
- Natural-language deterministic question engine
- Question-specific visualizations
- Better frontend error states
- No hardcoded Iris dataset logic

## Architecture

```text
CSV/XLSX/XLS
     |
     v
FastAPI
     |
     +--> Data Loader / Cache
     |
     +--> Profiler
     |
     +--> Analysis Engine
     |       +--> Statistics
     |       +--> Correlations
     |       +--> Outliers
     |       +--> Group Comparisons
     |       +--> Trends
     |
     +--> Question Engine
     |
     +--> Visualization Engine
     |
     v
React + Recharts Dashboard
```

## Project structure

```text
project/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── data_loader.py
│   │   ├── profiler.py
│   │   ├── analysis_engine.py
│   │   ├── visualization_engine.py
│   │   ├── question_engine.py
│   │   ├── quality_engine.py
│   │   └── schemas.py
│   └── requirements.txt
├── src/
│   ├── charts/
│   ├── components/
│   ├── pages/
│   └── services/
├── package.json
└── vite.config.ts
```

## Backend API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/upload` | Upload and profile a dataset |
| GET | `/dataset/{id}/profile` | Dataset profile |
| GET | `/dataset/{id}/preview?page=1&page_size=100` | Paginated preview |
| POST | `/dataset/{id}/analyze` | Full autonomous analysis |
| GET | `/dataset/{id}/charts` | Automatic visualizations |
| GET | `/dataset/{id}/quality` | Data quality report |
| GET | `/dataset/{id}/correlations` | Correlations |
| GET | `/dataset/{id}/outliers` | Outliers |
| POST | `/dataset/{id}/question` | Natural-language deterministic analysis |

## Run locally

### 1. Backend

```bash
cd backend

python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
.venv\Scriptsctivate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app.main:app --reload --port 8001
```

Backend:

```text
http://127.0.0.1:8001
```

### 2. Frontend

Open a second terminal in the project root:

```bash
npm install
npm run dev
```

Open the URL shown by Vite, normally:

```text
http://localhost:5173
```

The Vite configuration proxies `/api` to FastAPI on port `8001`.

## Large datasets

The application is designed so that the browser does not receive the entire dataset.

For large files:

- Profiling happens on the backend.
- Analysis happens on the backend.
- Preview is paginated.
- Scatter plots are sampled to a bounded number of points for rendering.
- Correlation heatmaps are bounded to the most informative numerical columns.
- Charts use aggregated data.
- No raw 50,000-row dataset is sent to a language model.

The core engine was tested with a synthetic 50,000-row dataset covering:

- profiling
- correlations
- outliers
- group comparisons
- trend analysis
- bar charts
- pie charts
- line charts
- scatter plots
- histograms
- box plots

## Important limitation

The question engine is intentionally **LLM-free**. It uses deterministic intent detection, keyword matching and dataset-column matching. It supports common questions about:

- averages
- medians
- totals
- minimum/maximum
- category comparisons
- counts
- correlations
- distributions
- trends
- missing values
- duplicates
- outliers

It does not claim to understand arbitrary human language like a general-purpose LLM.

## Tech stack

Frontend:

- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- Lucide React

Backend:

- Python
- FastAPI
- Pandas
- NumPy
- SciPy
- Scikit-learn
- openpyxl
- xlrd

## No Gemini dependency

This version intentionally does not call:

- Gemini
- OpenAI
- Claude
- Any external LLM API

All core data analysis is deterministic and local.
