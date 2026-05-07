import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Sparkles,
  Loader2,
  Filter,
  Wand2,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react';
import { runSmartQuery } from '../api';
import type { SmartQueryFilters, SmartQueryResponse } from '../api';

const STATUS_OPTIONS = ['', 'active', 'dormant', 'closed', 'unknown'];
const BUSINESS_TYPES = ['', 'factories', 'shop', 'pvt_ltd', 'partnership', 'proprietorship'];
const EVENT_TYPES = ['', 'inspection', 'renewal', 'filing', 'payment'];

const PRESETS: Array<{ label: string; description: string; filters: SmartQueryFilters }> = [
  {
    label: 'Active factories without recent inspection',
    description: 'The brief\'s killer query — Active + factories + no inspection in 18 months',
    filters: {
      status: 'active',
      business_type: 'factories',
      event_type: 'inspection',
      no_event_since_months: 18,
    },
  },
  {
    label: 'Dormant businesses for revival outreach',
    description: 'Dormant lifecycle status — candidates for re-engagement',
    filters: { status: 'dormant' },
  },
  {
    label: 'Closed businesses still flagged active in some source',
    description: 'Cross-system inconsistencies needing data-quality review',
    filters: { status: 'closed' },
  },
];

const STATUS_BADGE: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-800',
  dormant: 'bg-amber-100 text-amber-800',
  closed: 'bg-red-100 text-red-800',
  unknown: 'bg-gray-100 text-gray-600',
};

export default function Insights() {
  const [filters, setFilters] = useState<SmartQueryFilters>({
    status: 'active',
    business_type: 'factories',
    event_type: 'inspection',
    no_event_since_months: 18,
  });
  const [result, setResult] = useState<SmartQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (k: keyof SmartQueryFilters, v: string | number) => {
    setFilters((prev) => ({ ...prev, [k]: v === '' ? undefined : v }));
  };

  const submit = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await runSmartQuery(filters);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (preset: SmartQueryFilters) => {
    setFilters(preset);
    setTimeout(submit, 0);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Wand2 size={24} className="text-teal-600" />
          Smart Query — Cross-System Insights
        </h1>
        <p className="text-gray-500 mt-1">
          Ask questions that aren't possible without UBIDs. Filter by lifecycle status, pincode,
          sector, and event history across all 40+ Karnataka department systems.
        </p>
      </div>

      {/* Brief callout */}
      <div className="rounded-xl bg-gradient-to-br from-teal-50 to-cyan-50 border border-teal-200 p-4">
        <div className="flex items-start gap-3">
          <Sparkles size={18} className="text-teal-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-teal-900">
              From the brief: "Karnataka Commerce &amp; Industries can run queries impossible today"
            </p>
            <p className="text-sm text-teal-800 mt-1 italic">
              "Active factories in pin code 560058 with no inspection in the last 18 months"
            </p>
            <p className="text-xs text-teal-700 mt-2">
              Once UBIDs exist and lifecycle is inferred, this is one query. Click the preset
              below to run it.
            </p>
          </div>
        </div>
      </div>

      {/* Preset queries */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => applyPreset(p.filters)}
            className="text-left rounded-xl border border-gray-200 bg-white p-4 hover:border-teal-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-start gap-2">
              <div className="bg-teal-50 p-1.5 rounded-md">
                <Wand2 size={14} className="text-teal-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-sm">{p.label}</p>
                <p className="text-xs text-gray-500 mt-1">{p.description}</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Filter form */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={16} className="text-gray-500" />
          <h2 className="font-semibold text-gray-900">Filters</h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <Select
            label="Lifecycle Status"
            value={filters.status ?? ''}
            options={STATUS_OPTIONS}
            onChange={(v) => update('status', v)}
          />
          <Input
            label="Pincode"
            value={filters.pincode ?? ''}
            placeholder="e.g. 560058"
            onChange={(v) => update('pincode', v)}
          />
          <Select
            label="Business Type"
            value={filters.business_type ?? ''}
            options={BUSINESS_TYPES}
            onChange={(v) => update('business_type', v)}
          />
          <Input
            label="Sector"
            value={filters.sector ?? ''}
            placeholder="manufacturing"
            onChange={(v) => update('sector', v)}
          />
          <Select
            label="Event Type"
            value={filters.event_type ?? ''}
            options={EVENT_TYPES}
            onChange={(v) => update('event_type', v)}
          />
          <Input
            label="No Event Since (months)"
            value={filters.no_event_since_months?.toString() ?? ''}
            placeholder="18"
            type="number"
            onChange={(v) => update('no_event_since_months', v ? parseInt(v) : '')}
          />
        </div>

        <button
          onClick={submit}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-teal-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-teal-700 transition disabled:opacity-50"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          {loading ? 'Querying...' : 'Run Query'}
        </button>
      </div>

      {/* Results */}
      {error ? (
        <div className="rounded-xl bg-red-50 text-red-700 px-4 py-3 flex items-center gap-2">
          <AlertTriangle size={16} /> {error}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-4">
          {/* AI summary */}
          <div className="rounded-xl bg-gradient-to-br from-indigo-50 to-white border-l-4 border-indigo-500 border-y border-r border-indigo-100 p-5">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={16} className="text-indigo-600" />
              <span className="text-sm font-semibold text-indigo-700">AI Query Summary</span>
              <span className="text-[10px] uppercase tracking-wider rounded-full bg-indigo-600 text-white px-2 py-0.5 font-bold">
                Azure GPT-4.1
              </span>
              <span className="ml-auto text-2xl font-bold text-indigo-700">{result.total}</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{result.ai_summary}</p>
          </div>

          {/* Result table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                Matching businesses ({result.results.length} of {result.total})
              </h3>
            </div>
            {result.results.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-gray-500">
                No businesses match. Try widening filters.
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-2.5">UBID</th>
                    <th className="px-4 py-2.5">Business Name</th>
                    <th className="px-4 py-2.5">Pincode</th>
                    <th className="px-4 py-2.5">PAN</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5 text-right">Sources</th>
                    <th className="px-4 py-2.5">Last Event</th>
                    <th className="px-4 py-2.5"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.results.map((r) => (
                    <tr key={r.ubid} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-mono text-xs text-teal-700">{r.ubid}</td>
                      <td className="px-4 py-2.5 font-medium text-gray-900">{r.canonical_name}</td>
                      <td className="px-4 py-2.5 text-gray-600">{r.canonical_pincode || '—'}</td>
                      <td className="px-4 py-2.5 text-gray-600 font-mono text-xs">{r.canonical_pan || '—'}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[r.lifecycle_status?.toLowerCase()] ?? STATUS_BADGE.unknown}`}>
                          {r.lifecycle_status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right text-gray-600">{r.record_count}</td>
                      <td className="px-4 py-2.5 text-xs text-gray-500">
                        {r.last_event_date ? new Date(r.last_event_date).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="px-4 py-2.5">
                        <Link to={`/entity/${r.ubid}`} className="inline-flex items-center gap-1 text-teal-700 text-xs font-medium hover:text-teal-900">
                          Open <ArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Input({ label, value, placeholder, type = 'text', onChange }: {
  label: string; value: string; placeholder?: string; type?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
      />
    </div>
  );
}

function Select({ label, value, options, onChange }: {
  label: string; value: string; options: readonly string[];
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o ? o.replace(/_/g, ' ') : 'Any'}
          </option>
        ))}
      </select>
    </div>
  );
}
