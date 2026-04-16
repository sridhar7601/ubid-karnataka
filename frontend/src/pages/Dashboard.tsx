import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Upload,
  Play,
  Database,
  FileSpreadsheet,
  Users,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { getRecordStats, uploadRecords, runLinkage } from '../api';
import type { RecordStats, LinkageRunResult } from '../api';

const SOURCE_SYSTEMS = ['GST', 'MCA', 'Udyam'] as const;

export default function Dashboard() {
  const [stats, setStats] = useState<RecordStats | null>(null);
  const [statsError, setStatsError] = useState('');
  const [loading, setLoading] = useState(true);

  // Upload state
  const [uploadSource, setUploadSource] = useState<string>(SOURCE_SYSTEMS[0]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Linkage state
  const [running, setRunning] = useState(false);
  const [linkageResult, setLinkageResult] = useState<LinkageRunResult | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setStatsError('');
      const data = await getRecordStats();
      setStats(data);
    } catch (e: unknown) {
      setStatsError(e instanceof Error ? e.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setUploadMsg({ ok: false, text: 'Please upload a CSV file.' });
      return;
    }
    setUploading(true);
    setUploadMsg(null);
    try {
      const res = await uploadRecords(uploadSource, file);
      setUploadMsg({ ok: true, text: `${res.records_created} records imported from ${file.name}` });
      fetchStats();
    } catch (e: unknown) {
      setUploadMsg({ ok: false, text: e instanceof Error ? e.message : 'Upload failed' });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleRunLinkage = async () => {
    setRunning(true);
    setLinkageResult(null);
    try {
      const res = await runLinkage();
      setLinkageResult(res);
      fetchStats();
    } catch (e: unknown) {
      setLinkageResult({ status: 'error', pairs_found: 0, message: e instanceof Error ? e.message : 'Linkage failed' });
    } finally {
      setRunning(false);
    }
  };

  const sourceIcon: Record<string, typeof Database> = {
    GST: FileSpreadsheet,
    MCA: Database,
    Udyam: Users,
  };

  return (
    <div className="space-y-8">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Unified Business Identifier — overview and data ingestion
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {loading ? (
          <div className="col-span-full flex justify-center py-10">
            <Loader2 className="animate-spin text-teal-600" size={28} />
          </div>
        ) : statsError ? (
          <div className="col-span-full bg-red-50 text-red-700 rounded-xl p-4 flex items-center gap-2">
            <AlertCircle size={18} /> {statsError}
          </div>
        ) : stats ? (
          <>
            {/* Total records */}
            <StatCard
              label="Total Records"
              value={stats.total}
              icon={Database}
              color="teal"
            />
            {/* Per-source */}
            {SOURCE_SYSTEMS.map((s) => {
              const Icon = sourceIcon[s] ?? Database;
              return (
                <StatCard
                  key={s}
                  label={`${s} Records`}
                  value={stats.by_source[s] ?? 0}
                  icon={Icon}
                  color="cyan"
                />
              );
            })}
            {/* Unified */}
            <StatCard
              label="Unified Entities"
              value={stats.unified_count}
              icon={Users}
              color="emerald"
            />
          </>
        ) : null}
      </div>

      {/* Two-column: Upload + Linkage */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Upload size={18} className="text-teal-600" />
            Upload Records
          </h2>

          {/* Source selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source System
            </label>
            <select
              value={uploadSource}
              onChange={(e) => setUploadSource(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            >
              {SOURCE_SYSTEMS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Drag-drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-teal-400 bg-teal-50'
                : 'border-gray-300 hover:border-teal-300 hover:bg-gray-50'
            }`}
          >
            <Upload className="mx-auto mb-2 text-gray-400" size={28} />
            <p className="text-sm text-gray-600">
              Drag & drop a CSV file here, or{' '}
              <span className="text-teal-600 font-medium">browse</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Supports .csv files with entity records
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = '';
              }}
            />
          </div>

          {uploading && (
            <div className="flex items-center gap-2 text-sm text-teal-700">
              <Loader2 className="animate-spin" size={16} /> Uploading...
            </div>
          )}
          {uploadMsg && (
            <div
              className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 ${
                uploadMsg.ok
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-red-50 text-red-700'
              }`}
            >
              {uploadMsg.ok ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
              {uploadMsg.text}
            </div>
          )}
        </div>

        {/* Entity Resolution card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Play size={18} className="text-teal-600" />
            Entity Resolution
          </h2>
          <p className="text-sm text-gray-500">
            Run probabilistic record linkage across all uploaded source records.
            This uses Splink with IndicSoundex blocking to find matching entities
            across GST, MCA, and Udyam registries.
          </p>

          <button
            onClick={handleRunLinkage}
            disabled={running}
            className="inline-flex items-center gap-2 bg-teal-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {running ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                Running...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Entity Resolution
              </>
            )}
          </button>

          {linkageResult && (
            <div
              className={`rounded-lg px-4 py-3 text-sm ${
                linkageResult.status === 'error'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-emerald-50 text-emerald-700'
              }`}
            >
              <p className="font-medium">
                {linkageResult.status === 'error' ? 'Error' : 'Complete'}
              </p>
              <p>{linkageResult.message}</p>
              {linkageResult.pairs_found > 0 && (
                <p className="mt-1 font-semibold">
                  {linkageResult.pairs_found} candidate pairs found
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---- Reusable stat card ---- */

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: typeof Database;
  color: 'teal' | 'cyan' | 'emerald';
}) {
  const palette: Record<string, string> = {
    teal: 'bg-teal-50 text-teal-600',
    cyan: 'bg-cyan-50 text-cyan-600',
    emerald: 'bg-emerald-50 text-emerald-600',
  };
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${palette[color]}`}>
          <Icon size={18} />
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}
