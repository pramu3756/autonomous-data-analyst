const API_BASE = 'http://127.0.0.1:8000';

export interface Profile {
  dataset_name: string;
  file_size_bytes: number;
  rows: number;
  columns: number;
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  missing_values: number;
  missing_pct: number;
  duplicate_rows: number;
  constant_columns: string[];
  memory_usage_mb: number;
  column_details: ColumnDetail[];
}

export interface ColumnDetail {
  name: string;
  dtype: string;
  kind: 'numeric' | 'categorical' | 'datetime';
  non_null: number;
  null_count: number;
  null_pct: number;
  unique_count: number;
  mean?: number | null;
  median?: number | null;
  min?: number | null;
  max?: number | null;
  std?: number | null;
  q1?: number | null;
  q3?: number | null;
  iqr?: number | null;
  min_date?: string | null;
  max_date?: string | null;
  top_values?: { value: string; count: number; pct: number }[];
}

export interface UploadResponse {
  dataset_id: string;
  message: string;
  profile: Profile;
}

export interface PreviewResponse {
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface CorrelationResult {
  available: boolean;
  message?: string;
  columns: string[];
  matrix: (number | null)[][];
  pairs: { a: string; b: string; correlation: number; strength: string }[];
  strongest?: { a: string; b: string; correlation: number; strength: string } | null;
  strongest_positive?: { a: string; b: string; correlation: number; strength: string } | null;
  strongest_negative?: { a: string; b: string; correlation: number; strength: string } | null;
}

export interface OutlierResult {
  total_outliers: number;
  columns: {
    column: string;
    count: number;
    pct: number;
    lower_bound: number | null;
    upper_bound: number | null;
    q1: number | null;
    q3: number | null;
    iqr: number | null;
  }[];
}

export interface QualityResult {
  score: number;
  missing_values: number;
  missing_pct: number;
  duplicate_rows: number;
  outliers: number;
  outlier_columns: string[];
  constant_columns: string[];
  high_cardinality: string[];
  invalid_numeric: number;
  invalid_dates: number;
  issues: string[];
}

export interface Chart {
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'histogram' | 'box' | 'heatmap' | 'area';
  title: string;
  x_label?: string;
  y_label?: string;
  data?: any[];
  columns?: string[];
  matrix?: (number | null)[][];
}

export interface AnalysisResult {
  summary: string;
  numeric_stats: {
    column: string;
    mean: number | null;
    median: number | null;
    min: number | null;
    max: number | null;
    std: number | null;
    variance: number | null;
    range: number | null;
    q1: number | null;
    q3: number | null;
    iqr: number | null;
    skewness: number | null;
  }[];
  correlations: CorrelationResult;
  outliers: OutlierResult;
  group_comparisons: {
    category_column: string;
    numeric_column: string;
    title: string;
    data: { category: string; count: number; mean: number | null; median: number | null; min: number | null; max: number | null }[];
  }[];
  trends: {
    available: boolean;
    message?: string;
    date_column?: string;
    frequency?: string;
    trends?: { numeric_column: string; frequency: string; direction: string; series: { date: string; value: number | null }[] }[];
  };
  key_findings: { id: number; text: string }[];
}

export interface QuestionResult {
  intent: string;
  answer: string;
  data?: any;
  visualizations?: Chart[];
  suggestions?: string[];
  question?: string;
  ai_mode?: 'deterministic';
}

async function handle(res: Response): Promise<any> {
  if (!res.ok) {
    let detail = 'Request failed.';
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      detail = await res.text().catch(() => detail);
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  return handle(res);
}

export async function getProfile(id: string): Promise<Profile> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/profile`));
}

export async function getPreview(id: string, page = 1, pageSize = 100): Promise<PreviewResponse> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/preview?page=${page}&page_size=${pageSize}`));
}

export async function analyze(id: string): Promise<AnalysisResult> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/analyze`, { method: 'POST' }));
}

export async function getCharts(id: string): Promise<{ charts: Chart[] }> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/charts`));
}

export async function getQuality(id: string): Promise<QualityResult> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/quality`));
}

export async function getCorrelations(id: string): Promise<CorrelationResult> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/correlations`));
}

export async function getOutliers(id: string): Promise<OutlierResult> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/outliers`));
}

export async function askQuestion(id: string, question: string): Promise<QuestionResult> {
  return handle(await fetch(`${API_BASE}/dataset/${id}/question`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  }));
}
