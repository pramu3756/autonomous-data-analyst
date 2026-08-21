import { useState, useEffect, useMemo } from 'react';
import { Loader2, Table, Search, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { getPreview } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { PreviewResponse } from '@/services/api';

const PAGE_SIZE = 100;

export default function Preview() {
  const { datasetId } = useDataset();
  const [data, setData] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    getPreview(datasetId, page, PAGE_SIZE).then((d) => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, [datasetId, page]);

  const filteredRows = useMemo(() => {
    if (!data) return [];
    let rows = data.rows;
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter((r) => Object.values(r).some((v) => String(v ?? '').toLowerCase().includes(q)));
    }
    if (sortCol) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortCol], bv = b[sortCol];
        if (av == null) return 1;
        if (bv == null) return -1;
        if (typeof av === 'number' && typeof bv === 'number') return sortDir === 'asc' ? av - bv : bv - av;
        return sortDir === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
      });
    }
    return rows;
  }, [data, search, sortCol, sortDir]);

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  };

  if (loading || !data) return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2"><Table className="w-5 h-5 text-slate-600" /><h1 className="text-xl font-bold text-slate-800">Dataset Preview</h1></div>

      <div className="flex items-center justify-between gap-4">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search visible rows..."
            className="pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
          />
        </div>
        <p className="text-xs text-slate-500">Showing {filteredRows.length} of {data.total_rows.toLocaleString()} rows · Page {page} / {data.total_pages.toLocaleString()}</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase sticky top-0">
              <tr>
                <th className="px-3 py-2.5 font-medium text-slate-400">#</th>
                {data.columns.map((col) => (
                  <th key={col} className="text-left px-4 py-2.5 font-medium whitespace-nowrap">
                    <button onClick={() => toggleSort(col)} className="flex items-center gap-1 hover:text-slate-700">
                      {col}
                      <ArrowUpDown className={`w-3 h-3 ${sortCol === col ? 'text-blue-500' : 'text-slate-300'}`} />
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRows.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-3 py-2 text-slate-400 text-xs">{(page - 1) * PAGE_SIZE + i + 1}</td>
                  {data.columns.map((col) => {
                    const v = row[col];
                    return (
                      <td key={col} className="px-4 py-2 text-slate-700 whitespace-nowrap font-mono text-[12px] max-w-[240px] truncate" title={String(v ?? '')}>
                        {v === null || v === undefined ? <span className="text-slate-300">—</span> : String(v)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40"
        >
          <ChevronLeft className="w-4 h-4" /> Prev
        </button>
        <span className="text-sm text-slate-500">Page {page} of {data.total_pages.toLocaleString()}</span>
        <button
          onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
          disabled={page >= data.total_pages}
          className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40"
        >
          Next <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
