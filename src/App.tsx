import { useState, useCallback } from 'react';
import { Database, Plus } from 'lucide-react';
import { DatasetContext } from '@/services/datasetContext';
import type { Profile } from '@/services/api';
import Sidebar from '@/components/Sidebar';
import type { PageKey } from '@/components/Sidebar';
import UploadPage from '@/pages/UploadPage';
import Dashboard from '@/pages/Dashboard';
import Overview from '@/pages/Overview';
import Analysis from '@/pages/Analysis';
import Analytics from '@/pages/Analytics';
import Quality from '@/pages/Quality';
import Correlations from '@/pages/Correlations';
import Outliers from '@/pages/Outliers';
import Preview from '@/pages/Preview';

function App() {
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [page, setPage] = useState<PageKey>('dashboard');
  const [showUpload, setShowUpload] = useState(false);

  const setDataset = useCallback((id: string, p: Profile) => {
    setDatasetId(id);
    setProfile(p);
    setShowUpload(false);
    setPage('dashboard');
  }, []);

  const clearDataset = useCallback(() => {
    setDatasetId(null);
    setProfile(null);
    setPage('dashboard');
  }, []);

  const onUploaded = useCallback(() => {
    setShowUpload(false);
    setPage('dashboard');
  }, []);

  const showUploadScreen = !datasetId || showUpload;

  return (
    <DatasetContext.Provider value={{ datasetId, profile, setDataset, clearDataset }}>
      <div className="flex min-h-screen bg-slate-50 text-slate-800">
        <Sidebar current={page} onNavigate={setPage} />
        <main className="flex-1 min-w-0">
          <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
            <div className="flex items-center gap-2">
              {datasetId && profile && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-medium font-mono">{datasetId}</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-slate-600 truncate max-w-[280px]">{profile.dataset_name}</span>
                </div>
              )}
            </div>
            {datasetId && (
              <button
                onClick={() => setShowUpload(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" /> New Dataset
              </button>
            )}
          </header>

          <div className="p-6 max-w-[1400px] mx-auto">
            {showUploadScreen ? (
              <UploadPage onUploaded={onUploaded} />
            ) : (
              <>
                {page === 'dashboard' && <Dashboard />}
                {page === 'overview' && <Overview />}
                {page === 'analysis' && <Analysis />}
                {page === 'analytics' && <Analytics />}
                {page === 'quality' && <Quality />}
                {page === 'correlations' && <Correlations />}
                {page === 'outliers' && <Outliers />}
                {page === 'preview' && <Preview />}
              </>
            )}
          </div>
        </main>
      </div>
    </DatasetContext.Provider>
  );
}

export default App;
