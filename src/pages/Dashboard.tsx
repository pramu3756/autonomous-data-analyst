import { useState, useEffect } from 'react';
import { Database, Columns, Hash, Type, Calendar, FileWarning, Copy, MemoryStick, Loader2 } from 'lucide-react';
import { getProfile } from '@/services/api';
import { useDataset } from '@/services/datasetContext';
import type { Profile } from '@/services/api';
import StatCard from '@/components/StatCard';

export default function Dashboard() {
  const { datasetId, profile: ctxProfile } = useDataset();
  const [profile, setProfile] = useState<Profile | null>(ctxProfile);
  const [loading, setLoading] = useState(!ctxProfile);

  useEffect(() => {
    if (!datasetId) return;
    if (ctxProfile) { setProfile(ctxProfile); setLoading(false); return; }
    setLoading(true);
    getProfile(datasetId).then((p) => { setProfile(p); setLoading(false); }).catch(() => setLoading(false));
  }, [datasetId, ctxProfile]);

  if (loading || !profile) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-blue-600 animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">{profile.dataset_name} · {profile.rows.toLocaleString()} rows</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard icon={<Database className="w-5 h-5" />} label="Total Rows" value={profile.rows.toLocaleString()} accent="blue" />
        <StatCard icon={<Columns className="w-5 h-5" />} label="Total Columns" value={profile.columns} accent="slate" />
        <StatCard icon={<Hash className="w-5 h-5" />} label="Numeric Features" value={profile.numeric_columns.length} accent="cyan" />
        <StatCard icon={<Type className="w-5 h-5" />} label="Categorical Features" value={profile.categorical_columns.length} accent="amber" />
        <StatCard icon={<FileWarning className="w-5 h-5" />} label="Missing Values" value={profile.missing_values.toLocaleString()} accent="rose" sub={`${profile.missing_pct}% of cells`} />
        <StatCard icon={<Copy className="w-5 h-5" />} label="Duplicate Rows" value={profile.duplicate_rows.toLocaleString()} accent="slate" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 text-slate-600 mb-2"><Calendar className="w-4 h-4" /><span className="text-sm font-medium">Date Columns</span></div>
          {profile.datetime_columns.length ? (
            <ul className="text-sm text-slate-700 space-y-1">{profile.datetime_columns.map((c) => <li key={c} className="font-mono text-[13px]">{c}</li>)}</ul>
          ) : <p className="text-sm text-slate-400">No date columns detected.</p>}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 text-slate-600 mb-2"><MemoryStick className="w-4 h-4" /><span className="text-sm font-medium">Memory Usage</span></div>
          <p className="text-2xl font-bold text-slate-800">{profile.memory_usage_mb} MB</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 text-slate-600 mb-2"><FileWarning className="w-4 h-4" /><span className="text-sm font-medium">Constant Columns</span></div>
          {profile.constant_columns.length ? (
            <ul className="text-sm text-slate-700 space-y-1">{profile.constant_columns.map((c) => <li key={c} className="font-mono text-[13px]">{c}</li>)}</ul>
          ) : <p className="text-sm text-slate-400">None detected.</p>}
        </div>
      </div>
    </div>
  );
}
