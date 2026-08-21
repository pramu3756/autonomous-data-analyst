import { useState, useEffect } from 'react';
import { Loader2, Database } from 'lucide-react';
import { getProfile } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { ColumnDetail } from '@/services/api';

export default function Overview() {
  const { datasetId, profile: ctxProfile } = useDataset();
  const [profile, setProfile] = useState(ctxProfile);
  const [loading, setLoading] = useState(!ctxProfile);

  useEffect(() => {
    if (!datasetId) return;
    if (ctxProfile) { setProfile(ctxProfile); setLoading(false); return; }
    setLoading(true);
    getProfile(datasetId).then((p) => { setProfile(p); setLoading(false); }).catch(() => setLoading(false));
  }, [datasetId, ctxProfile]);

  if (loading || !profile) return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;

  const kindColor = (k: string) => k === 'numeric' ? 'bg-cyan-50 text-cyan-700' : k === 'datetime' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Database className="w-5 h-5 text-slate-600" />
        <h1 className="text-xl font-bold text-slate-800">Dataset Overview</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4"><p className="text-xs text-slate-500">File</p><p className="text-sm font-semibold text-slate-800 truncate">{profile.dataset_name}</p></div>
        <div className="bg-white rounded-xl border border-slate-200 p-4"><p className="text-xs text-slate-500">Size</p><p className="text-sm font-semibold text-slate-800">{(profile.file_size_bytes / 1024).toFixed(1)} KB</p></div>
        <div className="bg-white rounded-xl border border-slate-200 p-4"><p className="text-xs text-slate-500">Rows × Columns</p><p className="text-sm font-semibold text-slate-800">{profile.rows.toLocaleString()} × {profile.columns}</p></div>
        <div className="bg-white rounded-xl border border-slate-200 p-4"><p className="text-xs text-slate-500">Memory</p><p className="text-sm font-semibold text-slate-800">{profile.memory_usage_mb} MB</p></div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200"><h2 className="font-semibold text-slate-800 text-sm">Column Details</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Column</th>
                <th className="text-left px-4 py-2.5 font-medium">Type</th>
                <th className="text-left px-4 py-2.5 font-medium">Kind</th>
                <th className="text-right px-4 py-2.5 font-medium">Non-null</th>
                <th className="text-right px-4 py-2.5 font-medium">Null %</th>
                <th className="text-right px-4 py-2.5 font-medium">Unique</th>
                <th className="text-left px-4 py-2.5 font-medium">Stats</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {profile.column_details.map((col: ColumnDetail) => (
                <tr key={col.name} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-[13px] text-slate-800 font-medium">{col.name}</td>
                  <td className="px-4 py-2.5 text-slate-500 text-xs">{col.dtype}</td>
                  <td className="px-4 py-2.5"><span className={`px-2 py-0.5 rounded text-xs font-medium ${kindColor(col.kind)}`}>{col.kind}</span></td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{col.non_null.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{col.null_pct}%</td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{col.unique_count}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">
                    {col.kind === 'numeric' && col.mean != null && (
                      <span>μ={col.mean} · σ={col.std} · [{col.min}, {col.max}]</span>
                    )}
                    {col.kind === 'datetime' && col.min_date && (
                      <span>{col.min_date?.slice(0,10)} → {col.max_date?.slice(0,10)}</span>
                    )}
                    {col.kind === 'categorical' && col.top_values && col.top_values.length > 0 && (
                      <span>top: {col.top_values[0].value} ({col.top_values[0].pct}%)</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
