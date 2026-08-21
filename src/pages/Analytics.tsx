import { useState, useEffect } from 'react';
import { Loader2, PieChart as PieIcon } from 'lucide-react';
import { getCharts } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { Chart } from '@/services/api';
import ChartRenderer from '@/charts/ChartRenderer';

export default function Analytics() {
  const { datasetId } = useDataset();
  const [charts, setCharts] = useState<Chart[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    getCharts(datasetId).then((r) => { setCharts(r.charts); setLoading(false); }).catch((e) => { setError(e.message); setLoading(false); });
  }, [datasetId]);

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <PieIcon className="w-5 h-5 text-slate-600" />
        <h1 className="text-xl font-bold text-slate-800">Visual Analytics</h1>
      </div>

      {error && <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-sm text-rose-700">{error}</div>}

      {charts.length === 0 && !error ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <p className="text-slate-400 text-sm">No suitable visualization available for this analysis.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {charts.map((chart, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-800 mb-3">{chart.title}</h2>
              {chart.type === 'heatmap' ? (
                <ChartRenderer chart={chart} />
              ) : (chart.data && chart.data.length > 0) ? (
                <ChartRenderer chart={chart} />
              ) : (
                <p className="text-sm text-slate-400 py-12 text-center">No suitable visualization available for this analysis.</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
