import { useState, useEffect } from 'react';
import { Loader2, ShieldCheck, AlertTriangle, Copy, FileWarning, Type, AlertCircle } from 'lucide-react';
import { getQuality } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { QualityResult } from '@/services/api';

export default function Quality() {
  const { datasetId } = useDataset();
  const [quality, setQuality] = useState<QualityResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!datasetId) return;
    getQuality(datasetId).then((q) => { setQuality(q); setLoading(false); }).catch(() => setLoading(false));
  }, [datasetId]);

  if (loading || !quality) return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;

  const scoreColor = quality.score >= 80 ? 'text-emerald-600' : quality.score >= 60 ? 'text-amber-600' : 'text-rose-600';
  const ringColor = quality.score >= 80 ? '#059669' : quality.score >= 60 ? '#d97706' : '#dc2626';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-5 h-5 text-slate-600" />
        <h1 className="text-xl font-bold text-slate-800">Data Quality</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col items-center justify-center">
          <div className="relative w-32 h-32">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="44" fill="none" stroke="#e2e8f0" strokeWidth="8" />
              <circle cx="50" cy="50" r="44" fill="none" stroke={ringColor} strokeWidth="8" strokeLinecap="round" strokeDasharray={`${2 * Math.PI * 44 * quality.score / 100} ${2 * Math.PI * 44}`} />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-3xl font-bold ${scoreColor}`}>{quality.score}</span>
              <span className="text-xs text-slate-400">/ 100</span>
            </div>
          </div>
          <p className="text-sm font-medium text-slate-600 mt-3">Data Quality Score</p>
        </div>

        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <FileWarning className="w-5 h-5 text-rose-500 mb-2" />
            <p className="text-xs text-slate-500">Missing Values</p>
            <p className="text-xl font-bold text-slate-800">{quality.missing_pct}%</p>
            <p className="text-[11px] text-slate-400">{quality.missing_values.toLocaleString()} cells</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <Copy className="w-5 h-5 text-amber-500 mb-2" />
            <p className="text-xs text-slate-500">Duplicate Rows</p>
            <p className="text-xl font-bold text-slate-800">{quality.duplicate_rows}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <AlertTriangle className="w-5 h-5 text-orange-500 mb-2" />
            <p className="text-xs text-slate-500">Outliers</p>
            <p className="text-xl font-bold text-slate-800">{quality.outliers}</p>
            <p className="text-[11px] text-slate-400">{quality.outlier_columns.length} columns</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <Type className="w-5 h-5 text-slate-500 mb-2" />
            <p className="text-xs text-slate-500">Constant Columns</p>
            <p className="text-xl font-bold text-slate-800">{quality.constant_columns.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <AlertCircle className="w-5 h-5 text-cyan-500 mb-2" />
            <p className="text-xs text-slate-500">High Cardinality</p>
            <p className="text-xl font-bold text-slate-800">{quality.high_cardinality.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <AlertCircle className="w-5 h-5 text-rose-400 mb-2" />
            <p className="text-xs text-slate-500">Invalid Numeric</p>
            <p className="text-xl font-bold text-slate-800">{quality.invalid_numeric}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-800 mb-3">Detected Issues</h2>
        <ul className="space-y-2">
          {quality.issues.map((issue, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
              {issue}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
