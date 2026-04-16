import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Fingerprint,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Activity,
  Clock,
} from 'lucide-react';
import { getUnifiedEntity } from '../api';
import type { UnifiedEntity } from '../api';

const STATUS_STYLE: Record<string, string> = {
  Active: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  Dormant: 'bg-amber-100 text-amber-800 border-amber-300',
  Closed: 'bg-red-100 text-red-800 border-red-300',
  Unknown: 'bg-gray-100 text-gray-600 border-gray-300',
};

export default function EntityProfile() {
  const { ubid } = useParams<{ ubid: string }>();
  const [entity, setEntity] = useState<UnifiedEntity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchEntity = useCallback(async () => {
    if (!ubid) return;
    try {
      setError('');
      const data = await getUnifiedEntity(ubid);
      setEntity(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load entity');
    } finally {
      setLoading(false);
    }
  }, [ubid]);

  useEffect(() => {
    fetchEntity();
  }, [fetchEntity]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="animate-spin text-teal-600" size={32} />
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="space-y-4">
        <Link
          to="/entities"
          className="inline-flex items-center gap-1 text-sm text-teal-600 hover:text-teal-800"
        >
          <ArrowLeft size={14} /> Back to Unified Entities
        </Link>
        <div className="bg-red-50 text-red-700 rounded-xl p-4 flex items-center gap-2">
          <AlertCircle size={18} /> {error || 'Entity not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Back link */}
      <Link
        to="/entities"
        className="inline-flex items-center gap-1 text-sm text-teal-600 hover:text-teal-800"
      >
        <ArrowLeft size={14} /> Back to Unified Entities
      </Link>

      {/* Hero card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-teal-600 to-cyan-600 px-6 py-8 text-white">
          <div className="flex items-center gap-4">
            <div className="bg-white/20 backdrop-blur p-3 rounded-xl">
              <Fingerprint size={32} />
            </div>
            <div>
              <p className="text-teal-100 text-sm font-medium uppercase tracking-wider">
                Unified Business Identifier
              </p>
              <h1 className="text-3xl font-bold font-mono tracking-wide">
                {entity.ubid}
              </h1>
            </div>
          </div>
        </div>

        <div className="px-6 py-5 flex flex-wrap items-start gap-6">
          {/* Name + PAN */}
          <div className="flex-1 min-w-[200px]">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Canonical Name
            </p>
            <p className="text-lg font-semibold text-gray-900">
              {entity.canonical_name}
            </p>
            <p className="text-sm text-gray-500 mt-1">PAN: {entity.pan}</p>
          </div>

          {/* Lifecycle */}
          <div className="shrink-0">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
              Lifecycle Status
            </p>
            <span
              className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-full border ${STATUS_STYLE[entity.lifecycle_status] ?? STATUS_STYLE.Unknown}`}
            >
              <Activity size={14} />
              {entity.lifecycle_status}
            </span>
            {entity.lifecycle_reasoning && (
              <p className="text-xs text-gray-500 mt-2 max-w-xs">
                {entity.lifecycle_reasoning}
              </p>
            )}
          </div>

          {/* Record count */}
          <div className="shrink-0 text-right">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Linked Records
            </p>
            <p className="text-2xl font-bold text-teal-600">
              {entity.linked_record_count}
            </p>
          </div>
        </div>
      </div>

      {/* Linked records table */}
      {entity.linked_records && entity.linked_records.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">
              Linked Source Records
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="px-6 py-3 font-medium">Source</th>
                  <th className="px-6 py-3 font-medium">Entity Name</th>
                  <th className="px-6 py-3 font-medium">PAN</th>
                  <th className="px-6 py-3 font-medium">GSTIN</th>
                  <th className="px-6 py-3 font-medium">CIN</th>
                  <th className="px-6 py-3 font-medium">Udyam No.</th>
                  <th className="px-6 py-3 font-medium">State</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entity.linked_records.map((rec) => (
                  <tr key={rec.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3">
                      <span className="inline-flex items-center rounded-md bg-teal-50 px-2 py-0.5 text-xs font-medium text-teal-700">
                        {rec.source_system}
                      </span>
                    </td>
                    <td className="px-6 py-3 font-medium text-gray-900">
                      {rec.entity_name}
                    </td>
                    <td className="px-6 py-3 text-gray-600">{rec.pan || '-'}</td>
                    <td className="px-6 py-3 text-gray-600">{rec.gstin || '-'}</td>
                    <td className="px-6 py-3 text-gray-600">{rec.cin || '-'}</td>
                    <td className="px-6 py-3 text-gray-600">{rec.udyam_number || '-'}</td>
                    <td className="px-6 py-3 text-gray-600">{rec.state || '-'}</td>
                    <td className="px-6 py-3 text-gray-600">{rec.status || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Lifecycle timeline */}
      {entity.lifecycle_events && entity.lifecycle_events.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Clock size={18} className="text-teal-600" />
            Lifecycle Events
          </h2>
          <div className="relative pl-6 border-l-2 border-teal-200 space-y-6">
            {entity.lifecycle_events.map((ev, i) => (
              <div key={i} className="relative">
                {/* Dot */}
                <div className="absolute -left-[25px] top-1 w-3 h-3 rounded-full bg-teal-500 border-2 border-white" />
                <div>
                  <p className="text-sm font-semibold text-gray-900">{ev.event}</p>
                  <p className="text-xs text-gray-500">
                    {ev.date} &middot; Source: {ev.source}
                  </p>
                  {ev.details && (
                    <p className="text-xs text-gray-400 mt-1">{ev.details}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
