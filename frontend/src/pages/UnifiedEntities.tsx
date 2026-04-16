import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  Search,
  Loader2,
  AlertCircle,
  Activity,
  ExternalLink,
  Filter,
} from 'lucide-react';
import { listUnifiedEntities } from '../api';
import type { UnifiedEntity } from '../api';

const LIFECYCLE_OPTIONS = ['All', 'Active', 'Dormant', 'Closed', 'Unknown'] as const;

const STATUS_STYLE: Record<string, string> = {
  Active: 'bg-emerald-100 text-emerald-800',
  Dormant: 'bg-amber-100 text-amber-800',
  Closed: 'bg-red-100 text-red-800',
  Unknown: 'bg-gray-100 text-gray-600',
};

export default function UnifiedEntities() {
  const [entities, setEntities] = useState<UnifiedEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [searchText, setSearchText] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('All');

  const fetchEntities = useCallback(async () => {
    try {
      setError('');
      setLoading(true);
      const params: { lifecycle_status?: string; search?: string } = {};
      if (lifecycleFilter !== 'All') params.lifecycle_status = lifecycleFilter;
      if (searchText.trim()) params.search = searchText.trim();
      const data = await listUnifiedEntities(params);
      setEntities(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load entities');
    } finally {
      setLoading(false);
    }
  }, [lifecycleFilter, searchText]);

  useEffect(() => {
    const timer = setTimeout(fetchEntities, 300);
    return () => clearTimeout(timer);
  }, [fetchEntities]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Users size={24} className="text-teal-600" />
          Unified Entities
        </h1>
        <p className="text-gray-500 mt-1">
          Browse all resolved and unified business entities with their UBID.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-wrap items-center gap-4">
        <Filter size={16} className="text-gray-400" />

        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search by name, PAN, or UBID..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          />
        </div>

        {/* Lifecycle filter */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Status:</label>
          <select
            value={lifecycleFilter}
            onChange={(e) => setLifecycleFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          >
            {LIFECYCLE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <span className="text-xs text-gray-400 ml-auto">
          {entities.length} entit{entities.length !== 1 ? 'ies' : 'y'}
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
      ) : entities.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Users className="mx-auto mb-3" size={40} />
          <p>No unified entities found. Run Entity Resolution first.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="px-6 py-3 font-medium">UBID</th>
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-6 py-3 font-medium">PAN</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium text-center">Linked Records</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entities.map((ent) => (
                  <tr key={ent.ubid} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-mono text-sm text-teal-700 font-semibold">
                      {ent.ubid}
                    </td>
                    <td className="px-6 py-3 font-medium text-gray-900">
                      {ent.canonical_name}
                    </td>
                    <td className="px-6 py-3 text-gray-600">{ent.pan}</td>
                    <td className="px-6 py-3">
                      <span
                        className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_STYLE[ent.lifecycle_status] ?? STATUS_STYLE.Unknown}`}
                      >
                        <Activity size={12} />
                        {ent.lifecycle_status}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-center text-gray-600">
                      {ent.linked_record_count}
                    </td>
                    <td className="px-6 py-3">
                      <Link
                        to={`/entity/${ent.ubid}`}
                        className="inline-flex items-center gap-1 text-teal-600 hover:text-teal-800 text-sm font-medium"
                      >
                        View <ExternalLink size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
