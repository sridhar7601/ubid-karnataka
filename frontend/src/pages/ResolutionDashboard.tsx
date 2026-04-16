import { useCallback, useEffect, useState } from 'react';
import {
  GitMerge,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  Loader2,
  AlertCircle,
  Filter,
} from 'lucide-react';
import { getLinkageResults, reviewLinkage } from '../api';
import type { LinkagePair } from '../api';

const CONFIDENCE_LEVELS = [
  { label: 'All', min: 0, max: 1 },
  { label: 'High (>0.9)', min: 0.9, max: 1 },
  { label: 'Medium (0.7-0.9)', min: 0.7, max: 0.9 },
  { label: 'Low (<0.7)', min: 0, max: 0.7 },
] as const;

const STATUS_OPTIONS = ['all', 'pending_review', 'confirmed', 'rejected'] as const;

function confidenceColor(score: number): string {
  if (score >= 0.9) return 'bg-emerald-100 text-emerald-800';
  if (score >= 0.7) return 'bg-amber-100 text-amber-800';
  return 'bg-red-100 text-red-800';
}

function confidenceDot(score: number): string {
  if (score >= 0.9) return 'bg-emerald-500';
  if (score >= 0.7) return 'bg-amber-500';
  return 'bg-red-500';
}

function statusBadge(status: string): string {
  switch (status) {
    case 'confirmed':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'rejected':
      return 'bg-red-50 text-red-700 border-red-200';
    default:
      return 'bg-amber-50 text-amber-700 border-amber-200';
  }
}

export default function ResolutionDashboard() {
  const [pairs, setPairs] = useState<LinkagePair[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  // Filters
  const [confIdx, setConfIdx] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchPairs = useCallback(async () => {
    try {
      setError('');
      setLoading(true);
      const conf = CONFIDENCE_LEVELS[confIdx];
      const params: { min_score?: number; max_score?: number; status?: string } = {};
      if (conf.min > 0) params.min_score = conf.min;
      if (conf.max < 1) params.max_score = conf.max;
      if (statusFilter !== 'all') params.status = statusFilter;
      const data = await getLinkageResults(params);
      setPairs(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load linkage results');
    } finally {
      setLoading(false);
    }
  }, [confIdx, statusFilter]);

  useEffect(() => {
    fetchPairs();
  }, [fetchPairs]);

  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleReview = async (id: number, decision: 'confirmed' | 'rejected') => {
    try {
      const updated = await reviewLinkage(id, decision);
      setPairs((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: updated.status } : p)),
      );
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <GitMerge size={24} className="text-teal-600" />
          Entity Resolution Results
        </h1>
        <p className="text-gray-500 mt-1">
          Review candidate linkage pairs and confirm or reject matches.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-wrap items-center gap-4">
        <Filter size={16} className="text-gray-400" />

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Confidence:</label>
          <select
            value={confIdx}
            onChange={(e) => setConfIdx(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          >
            {CONFIDENCE_LEVELS.map((c, i) => (
              <option key={i} value={i}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All' : s.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        <span className="text-xs text-gray-400 ml-auto">
          {pairs.length} pair{pairs.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-teal-600" size={28} />
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-700 rounded-xl p-4 flex items-center gap-2">
          <AlertCircle size={18} /> {error}
        </div>
      ) : pairs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <GitMerge className="mx-auto mb-3" size={40} />
          <p>No linkage pairs found. Run Entity Resolution from the Dashboard first.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pairs.map((pair) => {
            const isOpen = expanded.has(pair.id);
            return (
              <div
                key={pair.id}
                className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden"
              >
                {/* Summary row */}
                <button
                  onClick={() => toggleExpand(pair.id)}
                  className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-gray-50 transition-colors"
                >
                  {/* Confidence dot */}
                  <div className={`w-3 h-3 rounded-full shrink-0 ${confidenceDot(pair.overall_score)}`} />

                  {/* Record A */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">
                      {pair.record_a.entity_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {pair.record_a.source_system} &middot; PAN: {pair.record_a.pan || 'N/A'}
                    </p>
                  </div>

                  {/* VS */}
                  <div className="text-xs font-bold text-gray-300 uppercase">vs</div>

                  {/* Record B */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">
                      {pair.record_b.entity_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {pair.record_b.source_system} &middot; PAN: {pair.record_b.pan || 'N/A'}
                    </p>
                  </div>

                  {/* Score badge */}
                  <span
                    className={`text-xs font-semibold px-2.5 py-1 rounded-full ${confidenceColor(pair.overall_score)}`}
                  >
                    {(pair.overall_score * 100).toFixed(1)}%
                  </span>

                  {/* Status badge */}
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full border capitalize ${statusBadge(pair.status)}`}
                  >
                    {pair.status.replace('_', ' ')}
                  </span>

                  {/* Expand icon */}
                  {isOpen ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </button>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="border-t border-gray-100 px-5 py-4 bg-gray-50 space-y-4">
                    {/* Score breakdown */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <ScoreChip label="Name Similarity" value={pair.name_similarity} />
                      <ScoreChip label="Address Similarity" value={pair.address_similarity} />
                      <ScoreChip label="PAN Match" value={pair.pan_match ? 1 : 0} boolean />
                      <ScoreChip label="Pincode Match" value={pair.pincode_match ? 1 : 0} boolean />
                    </div>

                    {/* Actions */}
                    {pair.status === 'pending_review' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleReview(pair.id, 'confirmed')}
                          className="inline-flex items-center gap-1.5 bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
                        >
                          <Check size={14} /> Accept
                        </button>
                        <button
                          onClick={() => handleReview(pair.id, 'rejected')}
                          className="inline-flex items-center gap-1.5 bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                        >
                          <X size={14} /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ScoreChip({
  label,
  value,
  boolean: isBool,
}: {
  label: string;
  value: number;
  boolean?: boolean;
}) {
  const display = isBool
    ? value === 1
      ? 'Yes'
      : 'No'
    : `${(value * 100).toFixed(1)}%`;
  const color = isBool
    ? value === 1
      ? 'text-emerald-700 bg-emerald-50'
      : 'text-red-700 bg-red-50'
    : value >= 0.9
      ? 'text-emerald-700 bg-emerald-50'
      : value >= 0.7
        ? 'text-amber-700 bg-amber-50'
        : 'text-red-700 bg-red-50';

  return (
    <div className={`rounded-lg px-3 py-2 ${color}`}>
      <p className="text-xs opacity-70">{label}</p>
      <p className="text-sm font-bold">{display}</p>
    </div>
  );
}
