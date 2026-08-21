import { useState, useEffect } from 'react';
import { Loader2, AlertTriangle } from 'lucide-react';
import { getOutliers } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { OutlierResult } from '@/services/api';

export default function Outliers() {
  const { datasetId } = useDataset();
  const [outl, setOutl] = useState<OutlierResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!datasetId) return;
    getOutliers(datasetId).then((o) => { setOutl(o); setLoading(false); }).catch(() => setLoading(false));
  }, [datasetId]);

  if (loading || !outl) return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-slate-600" /><h1 className="text-xl font-bold text-slate-800">Outliers</h1></div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-500">Total Outliers</p>
          <p className="text-3xl font-bold text-rose-600 mt-1">{outl.total_outliers}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-500">Affected Columns</p>
          <p className="text-3xl font-bold text-slate-800 mt-1">{outl.columns.filter((c) => c.count > 0).length}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-500">Detection Method</p>
          <p className="text-sm font-semibold text-slate-800 mt-1">IQR (1.5×)</p>
        </div>
      </div>

      {outl.columns.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center"><p className="text-sm text-slate-400">No numerical columns found for outlier detection.</p></div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Column</th>
                <th className="text-right px-4 py-2.5 font-medium">Outliers</th>
                <th className="text-right px-4 py-2.5 font-medium">% of values</th>
                <th className="text-right px-4 py-2.5 font-medium">Q1</th>
                <th className="text-right px-4 py-2.5 font-medium">Q3</th>
                <th className="text-right px-4 py-2.5 font-medium">IQR</th>
                <th className="text-right px-4 py-2.5 font-medium">Lower bound</th>
                <th className="text-right px-4 py-2.5 font-medium">Upper bound</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {outl.columns.map((c) => (
                <tr key={c.column} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-[13px] font-medium text-slate-800">{c.column}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={c.count > 0 ? 'font-semibold text-rose-600' : 'text-slate-400'}>{c.count}</span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{c.pct}%</td>
                  <td className="px-4 py-2.5 text-right text-slate-600">{c.q1}</td>
                  <td className="px-4 py-2.5 text-right text-slate-600">{c.q3}</td>
                  <td className="px-4 py-2.5 text-right text-slate-600">{c.iqr}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{c.lower_bound}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{c.upper_bound}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
