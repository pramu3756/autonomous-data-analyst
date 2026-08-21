import { LayoutDashboard, Database, BarChart3, PieChart, ShieldCheck, GitCompare, AlertTriangle, Table } from 'lucide-react';
import { useDataset } from '@/services/datasetContext';

export type PageKey = 'dashboard' | 'overview' | 'analysis' | 'analytics' | 'quality' | 'correlations' | 'outliers' | 'preview';

interface SidebarProps {
  current: PageKey;
  onNavigate: (page: PageKey) => void;
}

const NAV_ITEMS: { key: PageKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'overview', label: 'Dataset Overview', icon: Database },
  { key: 'analysis', label: 'Data Analysis', icon: BarChart3 },
  { key: 'analytics', label: 'Analytics', icon: PieChart },
  { key: 'quality', label: 'Data Quality', icon: ShieldCheck },
  { key: 'correlations', label: 'Correlations', icon: GitCompare },
  { key: 'outliers', label: 'Outliers', icon: AlertTriangle },
  { key: 'preview', label: 'Dataset Preview', icon: Table },
];

export default function Sidebar({ current, onNavigate }: SidebarProps) {
  const { datasetId } = useDataset();
  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col h-screen sticky top-0 shrink-0">
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-white font-semibold text-[15px] leading-tight">DataPilot</h1>
            <p className="text-[11px] text-slate-400 leading-tight">Autonomous Data Analyst</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = current === item.key;
          const disabled = !datasetId && item.key !== 'dashboard';
          return (
            <button
              key={item.key}
              onClick={() => !disabled && onNavigate(item.key)}
              disabled={disabled}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? 'bg-blue-600 text-white'
                  : disabled
                    ? 'text-slate-600 cursor-not-allowed'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Icon className="w-[18px] h-[18px]" />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-slate-800">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <div>
            <p className="text-[12px] text-white font-medium leading-tight">Analyst Online</p>
            <p className="text-[10px] text-slate-400 leading-tight">Deterministic Analysis Engine</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
