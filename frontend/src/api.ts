const BASE = '/api';

export interface Record {
  id: number;
  source_system: string;
  entity_name: string;
  pan: string;
  gstin?: string;
  cin?: string;
  udyam_number?: string;
  address?: string;
  state?: string;
  pincode?: string;
  registration_date?: string;
  status?: string;
  created_at: string;
}

export interface RecordStats {
  total: number;
  by_source: { [source: string]: number };
  unified_count: number;
}

export interface LinkagePair {
  id: number;
  record_a_id: number;
  record_b_id: number;
  record_a: Record;
  record_b: Record;
  overall_score: number;
  name_similarity: number;
  address_similarity: number;
  pan_match: boolean;
  pincode_match: boolean;
  status: 'pending_review' | 'confirmed' | 'rejected';
  created_at: string;
}

export interface LinkageRunResult {
  status: string;
  pairs_found: number;
  message: string;
}

export interface LifecycleEvent {
  date: string;
  event: string;
  source: string;
  details?: string;
}

export interface UnifiedEntity {
  ubid: string;
  canonical_name: string;
  pan: string;
  lifecycle_status: 'Active' | 'Dormant' | 'Closed' | 'Unknown';
  lifecycle_reasoning?: string;
  linked_record_count: number;
  linked_records?: Record[];
  lifecycle_events?: LifecycleEvent[];
  created_at: string;
  updated_at: string;
}

// ---------- Records ----------

export async function uploadRecords(sourceSystem: string, file: File): Promise<{ message: string; records_created: number }> {
  const form = new FormData();
  form.append('source_system', sourceSystem);
  form.append('file', file);
  const res = await fetch(`${BASE}/records/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listRecords(sourceSystem?: string): Promise<Record[]> {
  const params = new URLSearchParams();
  if (sourceSystem) params.set('source_system', sourceSystem);
  const res = await fetch(`${BASE}/records/?${params}`);
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.records ?? data;
}

export async function getRecordStats(): Promise<RecordStats> {
  const res = await fetch(`${BASE}/records/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---------- Linkage ----------

export async function runLinkage(): Promise<LinkageRunResult> {
  const res = await fetch(`${BASE}/linkage/run`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLinkageResults(params?: {
  min_score?: number;
  max_score?: number;
  status?: string;
}): Promise<LinkagePair[]> {
  const search = new URLSearchParams();
  if (params?.min_score !== undefined) search.set('min_score', String(params.min_score));
  if (params?.max_score !== undefined) search.set('max_score', String(params.max_score));
  if (params?.status) search.set('status', params.status);
  const res = await fetch(`${BASE}/linkage/results?${search}`);
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.results ?? data;
}

export async function reviewLinkage(id: number, decision: 'confirmed' | 'rejected'): Promise<LinkagePair> {
  const res = await fetch(`${BASE}/linkage/${id}/review`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: decision }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---------- Unified ----------

export async function listUnifiedEntities(params?: {
  lifecycle_status?: string;
  search?: string;
}): Promise<UnifiedEntity[]> {
  const search = new URLSearchParams();
  if (params?.lifecycle_status) search.set('lifecycle_status', params.lifecycle_status);
  if (params?.search) search.set('search', params.search);
  const res = await fetch(`${BASE}/unified/?${search}`);
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.entities ?? data;
}

export async function getUnifiedEntity(ubid: string): Promise<UnifiedEntity> {
  const res = await fetch(`${BASE}/unified/${ubid}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
