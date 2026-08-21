import { useState, useEffect } from 'react';
import { Loader2, GitCompare } from 'lucide-react';
import { getCorrelations } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { CorrelationResult, Chart } from '@/services/api';
import ChartRenderer from '@/charts/ChartRenderer';

export default function Correlations() {
  const { datasetId } = useDataset();
  const [corr, setCorr] = useState<CorrelationResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!datasetId) return;
    getCorrelations(datasetId).then((c) => { setCorr(c); setLoading(false); }).catch(() => setLoading(false));
  }, [datasetId]);

  if (loading || !corr) return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;

  if (!corr.available) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2"><GitCompare className="w-5 h-5 text-slate-600" /><h1 className="text-xl font-bold text-slate-800">Correlations</h1></div>
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center"><p className="text-sm text-slate-400">{corr.message}</p></div>
      </div>
    );
  }

  const strengthColor = (s: string) => s === 'strong' ? 'bg-emerald-50 text-emerald-700' : s === 'moderate' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2"><GitCompare className="w-5 h-5 text-slate-600" /><h1 className="text-xl font-bold text-slate-800">Correlations</h1></div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {corr.strongest && (
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Strongest Correlation</p>
            <p className="text-sm font-semibold text-slate-800">{corr.strongest.a} ↔ {corr.strongest.b}</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{corr.strongest.correlation}</p>
          </div>
        )}
        {corr.strongest_positive && (
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Strongest Positive</p>
            <p className="text-sm font-semibold text-slate-800">{corr.strongest_positive.a} ↔ {corr.strongest_positive.b}</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">+{corr.strongest_positive.correlation}</p>
          </div>
        )}
        {corr.strongest_negative && (
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Strongest Negative</p>
            <p className="text-sm font-semibold text-slate-800">{corr.strongest_negative.a} ↔ {corr.strongest_negative.b}</p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{corr.strongest_negative.correlation}</p>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-800 mb-3">Correlation Matrix</h2>
        <ChartRenderer chart={{ type: 'heatmap', title: 'Correlation Matrix', columns: corr.columns, matrix: corr.matrix }} />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200"><h2 className="font-semibold text-slate-800 text-sm">All Correlation Pairs</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr><th className="text-left px-4 py-2.5 font-medium">Feature A</th><th className="text-left px-4 py-2.5 font-medium">Feature B</th><th className="text-right px-4 py-2.5 font-medium">r</th><th className="text-left px-4 py-2.5 font-medium">Strength</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {corr.pairs.map((p, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-[13px] text-slate-800">{p.a}</td>
                  <td className="px-4 py-2.5 font-mono text-[13px] text-slate-800">{p.b}</td>
                  <td className="px-4 py-2.5 text-right font-medium text-slate-700">{p.correlation}</td>
                  <td className="px-4 py-2.5"><span className={`px-2 py-0.5 rounded text-xs font-medium ${strengthColor(p.strength)}`}>{p.strength}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
