import { useState, useRef, useCallback } from 'react';
import { UploadCloud, FileSpreadsheet, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { uploadFile } from '@/services/api';
import { useDataset } from '@/services/datasetContext';

interface UploadPageProps {
  onUploaded: () => void;
}

const LOADING_MESSAGES = [
  'Processing dataset...',
  'Calculating statistics...',
  'Detecting relationships...',
  'Generating visualizations...',
];

export default function UploadPage({ onUploaded }: UploadPageProps) {
  const { setDataset } = useDataset();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setUploading(true);
    setProgress(0);
    const timer = setInterval(() => setProgress((p) => (p < 90 ? p + 10 : p)), 250);
    try {
      const res = await uploadFile(file);
      setDataset(res.dataset_id, res.profile);
      setProgress(100);
      setTimeout(() => onUploaded(), 500);
    } catch (e: any) {
      setError(e.message || 'Unable to upload the file.');
    } finally {
      clearInterval(timer);
      setUploading(false);
    }
  }, [setDataset, onUploaded]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="max-w-2xl mx-auto py-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto mb-4">
          <UploadCloud className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl font-bold text-slate-800">Upload your dataset</h1>
        <p className="text-slate-500 mt-1">Drop a CSV, XLSX, or XLS file to begin autonomous analysis.</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors ${
          dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50'
        } ${uploading ? 'pointer-events-none' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {uploading ? (
          <div className="space-y-4">
            <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto" />
            <p className="text-slate-700 font-medium">{LOADING_MESSAGES[Math.min(progress / 25, 3) | 0]}</p>
            <div className="w-full max-w-xs mx-auto bg-slate-200 rounded-full h-2 overflow-hidden">
              <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <FileSpreadsheet className="w-10 h-10 text-slate-400 mx-auto" />
            <p className="text-lg font-semibold text-slate-700">Drop your dataset here</p>
            <p className="text-sm text-slate-400">or browse files</p>
            <p className="text-[11px] text-slate-400 mt-2">Supported: CSV, XLSX, XLS · Max 100 MB</p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 flex items-start gap-2 bg-rose-50 border border-rose-200 rounded-lg p-3 text-sm text-rose-700">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
        <span>Analysis runs locally — your data never leaves this server.</span>
      </div>
    </div>
  );
}
