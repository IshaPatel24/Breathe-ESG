import React, { useState, useEffect } from 'react';
import { 
  Check, X, Flag, Lock, Info, Filter, RefreshCw, ChevronLeft, ChevronRight, 
  Layers, Database, ClipboardCheck, Ban, HelpCircle, Activity 
} from 'lucide-react';
import { apiRequest } from '../api';
import AuditTrailModal from './AuditTrailModal';

export default function ReviewDashboard({ initialBatchFilter, onClearBatchFilter }) {
  // Records state
  const [records, setRecords] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters state
  const [status, setStatus] = useState('');
  const [scope, setScope] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [batchId, setBatchId] = useState(initialBatchFilter || '');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Dashboard Stats summary
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Detail Modal & Flag Modal states
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [flaggingRecord, setFlaggingRecord] = useState(null);
  const [flagReason, setFlagReason] = useState('');
  const [flagError, setFlagError] = useState(null);

  useEffect(() => {
    // Sync batch filter if changed from parent
    setBatchId(initialBatchFilter || '');
    setPage(1);
  }, [initialBatchFilter]);

  // Reload records when filters or page changes
  useEffect(() => {
    fetchRecords();
  }, [page, status, scope, sourceType, batchId, startDate, endDate]);

  // Load dashboard stats when filters change (to reflect current tenant metrics)
  useEffect(() => {
    fetchDashboardStats();
  }, [batchId]); // Refresh stats when batch changes, or call inside updates

  async function fetchRecords() {
    setLoading(true);
    setError(null);
    try {
      let query = `/api/records/?page=${page}`;
      if (status) query += `&status=${status}`;
      if (scope) query += `&scope=${scope}`;
      if (sourceType) query += `&source_type=${sourceType}`;
      if (batchId) query += `&batch_id=${batchId}`;
      if (startDate) query += `&period_start=${startDate}`;
      if (endDate) query += `&period_end=${endDate}`;

      const data = await apiRequest(query);
      setRecords(data.results || []);
      setCount(data.count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchDashboardStats() {
    setStatsLoading(true);
    try {
      const data = await apiRequest('/api/dashboard/summary/');
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch dashboard stats:", err);
    } finally {
      setStatsLoading(false);
    }
  }

  // Inline Record Actions
  async function handleApprove(recordId, e) {
    e.stopPropagation();
    try {
      const updated = await apiRequest(`/api/records/${recordId}/approve/`, { method: 'POST' });
      updateRecordInState(updated);
      fetchDashboardStats();
    } catch (err) {
      alert(`Approval failed: ${err.message}`);
    }
  }

  async function handleReject(recordId, e) {
    e.stopPropagation();
    try {
      const updated = await apiRequest(`/api/records/${recordId}/reject/`, { method: 'POST' });
      updateRecordInState(updated);
      fetchDashboardStats();
    } catch (err) {
      alert(`Rejection failed: ${err.message}`);
    }
  }

  function openFlagModal(record, e) {
    e.stopPropagation();
    setFlaggingRecord(record);
    setFlagReason('');
    setFlagError(null);
  }

  async function handleFlagSubmit(e) {
    e.preventDefault();
    if (!flagReason.trim()) {
      setFlagError("Please provide a reason for flagging this record.");
      return;
    }

    try {
      const updated = await apiRequest(`/api/records/${flaggingRecord.id}/flag/`, {
        method: 'POST',
        body: { flag_reason: flagReason }
      });
      updateRecordInState(updated);
      setFlaggingRecord(null);
      fetchDashboardStats();
    } catch (err) {
      setFlagError(err.message);
    }
  }

  function updateRecordInState(updatedRecord) {
    setRecords(prev => prev.map(rec => rec.id === updatedRecord.id ? updatedRecord : rec));
    if (selectedRecord && selectedRecord.id === updatedRecord.id) {
      setSelectedRecord(updatedRecord);
    }
  }

  function clearAllFilters() {
    setStatus('');
    setScope('');
    setSourceType('');
    setStartDate('');
    setEndDate('');
    setBatchId('');
    if (onClearBatchFilter) onClearBatchFilter();
    setPage(1);
  }

  // Format Helpers
  const getStatusConfig = (status, isLocked) => {
    if (isLocked && status === 'APPROVED') {
      return { label: 'Locked Audit-Ready', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', icon: <Lock className="w-3.5 h-3.5 mr-1" /> };
    }
    if (isLocked && status === 'REJECTED') {
      return { label: 'Locked Rejected', badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20', icon: <Lock className="w-3.5 h-3.5 mr-1" /> };
    }
    const configs = {
      PENDING_REVIEW: { label: 'Pending Review', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
      APPROVED: { label: 'Approved', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
      REJECTED: { label: 'Rejected', badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
      FLAGGED: { label: 'Flagged', badge: 'bg-orange-500/10 text-orange-400 border-orange-500/20' }
    };
    return configs[status] || configs.PENDING_REVIEW;
  };

  const getScopeLabel = (scope) => {
    return scope.replace('_', ' ');
  };

  const getCategoryLabel = (cat) => {
    return cat.replace('_', ' ');
  };

  const totalPages = Math.ceil(count / 50) || 1;

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* 1. Dashboard Stats Cards */}
      {stats && !statsLoading && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="glass-card rounded-2xl p-5 border-l-4 border-l-brand-500">
            <span className="text-xs text-slate-500 uppercase font-semibold">Verification Queue</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold text-slate-200">
                {stats.status_counts.PENDING_REVIEW}
              </span>
              <span className="text-xs text-slate-500">rows pending</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-2 block">
              Flagged: {stats.status_counts.FLAGGED} | Approved: {stats.status_counts.APPROVED}
            </p>
          </div>

          <div className="glass-card rounded-2xl p-5 border-l-4 border-l-status-approved">
            <span className="text-xs text-slate-500 uppercase font-semibold">Scope 1 Activity (Fuel)</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-2xl font-bold text-slate-200">
                {Math.round(stats.activity_by_scope.SCOPE_1.approved).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">L / kg / m3</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-2">
              Total uploaded: {Math.round(stats.activity_by_scope.SCOPE_1.total).toLocaleString()}
            </p>
          </div>

          <div className="glass-card rounded-2xl p-5 border-l-4 border-l-sky-500">
            <span className="text-xs text-slate-500 uppercase font-semibold">Scope 2 (Electricity)</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-2xl font-bold text-slate-200">
                {Math.round(stats.activity_by_scope.SCOPE_2.approved).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">kWh</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-2">
              Total uploaded: {Math.round(stats.activity_by_scope.SCOPE_2.total).toLocaleString()}
            </p>
          </div>

          <div className="glass-card rounded-2xl p-5 border-l-4 border-l-accent-500">
            <span className="text-xs text-slate-500 uppercase font-semibold">Scope 3 (Travel & Goods)</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-2xl font-bold text-slate-200">
                {Math.round(stats.activity_by_scope.SCOPE_3.approved).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">km / nights</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-2">
              Total uploaded: {Math.round(stats.activity_by_scope.SCOPE_3.total).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* 2. Advanced Multi-Filter Selector Panel */}
      <div className="glass rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-brand-500" />
            <h3 className="text-sm font-bold text-slate-200">Refine Ingested Records</h3>
          </div>
          <button 
            onClick={clearAllFilters}
            className="text-xs text-slate-400 hover:text-slate-100 flex items-center gap-1 bg-slate-850 hover:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-800/80 transition-colors"
          >
            Clear Filters
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 text-xs">
          <div>
            <label className="text-slate-500 font-semibold block mb-1">Source Type</label>
            <select 
              value={sourceType} 
              onChange={(e) => { setSourceType(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-slate-350 focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Sources</option>
              <option value="SAP">SAP (Fuel & Goods)</option>
              <option value="UTILITY">Utility Portal (Electricity)</option>
              <option value="TRAVEL">Corporate Travel</option>
            </select>
          </div>

          <div>
            <label className="text-slate-500 font-semibold block mb-1">Scope Category</label>
            <select 
              value={scope} 
              onChange={(e) => { setScope(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-slate-350 focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Scopes</option>
              <option value="SCOPE_1">Scope 1 (Direct Fuel)</option>
              <option value="SCOPE_2">Scope 2 (Electricity)</option>
              <option value="SCOPE_3">Scope 3 (Travel / Goods)</option>
            </select>
          </div>

          <div>
            <label className="text-slate-500 font-semibold block mb-1">Audit Status</label>
            <select 
              value={status} 
              onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-slate-350 focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="APPROVED">Approved & Locked</option>
              <option value="REJECTED">Rejected & Locked</option>
              <option value="FLAGGED">Flagged Suspicious</option>
            </select>
          </div>

          <div>
            <label className="text-slate-500 font-semibold block mb-1">Period Start</label>
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 p-2 rounded-xl text-slate-350 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-500 font-semibold block mb-1">Period End</label>
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 p-2 rounded-xl text-slate-350 focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        {batchId && (
          <div className="flex items-center gap-2 pt-2 text-xs">
            <span className="text-slate-500 font-semibold">Active Filter:</span>
            <span className="px-2.5 py-1 bg-brand-500/10 text-brand-400 border border-brand-500/20 rounded-lg flex items-center gap-1.5 font-mono">
              Batch: {batchId}
              <button 
                onClick={() => { setBatchId(''); if(onClearBatchFilter) onClearBatchFilter(); }}
                className="hover:text-slate-100 font-bold ml-1"
              >
                ×
              </button>
            </span>
          </div>
        )}
      </div>

      {/* 3. Records Table */}
      <div className="glass border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="p-5 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-bold text-slate-200">Unified Activity Log</h3>
            <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
              {count} records
            </span>
          </div>
          <button 
            onClick={fetchRecords}
            className="p-2 text-slate-400 hover:text-slate-200 bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-lg transition-all"
            title="Refresh logs"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 bg-slate-950/10">
            <div className="w-8 h-8 border-3 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500 mt-3">Fetching records...</span>
          </div>
        ) : error ? (
          <div className="p-6 text-center text-rose-400 bg-rose-500/5">{error}</div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Activity className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="font-semibold text-sm">No activity records match these filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-950/40 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-4">Source</th>
                  <th className="py-3.5 px-4">Scope</th>
                  <th className="py-3.5 px-4">Category</th>
                  <th className="py-3.5 px-4">Period Range</th>
                  <th className="py-3.5 px-4">Facility Site</th>
                  <th className="py-3.5 px-4 text-right">Value</th>
                  <th className="py-3.5 px-4">Unit</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900/10">
                {records.map((rec) => {
                  const stat = getStatusConfig(rec.status, rec.is_locked);
                  
                  return (
                    <tr 
                      key={rec.id}
                      onClick={() => setSelectedRecord(rec)}
                      className={`hover:bg-slate-950/30 transition-colors cursor-pointer group ${
                        rec.is_locked ? 'opacity-60 bg-slate-950/15' : ''
                      }`}
                    >
                      <td className="py-4 px-4 font-bold text-slate-300">
                        {rec.source_type}
                      </td>
                      <td className="py-4 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          rec.scope === 'SCOPE_1' 
                            ? 'bg-status-approved/10 text-status-approved'
                            : rec.scope === 'SCOPE_2'
                              ? 'bg-sky-500/10 text-sky-400'
                              : 'bg-accent-500/10 text-accent-400'
                        }`}>
                          {getScopeLabel(rec.scope)}
                        </span>
                      </td>
                      <td className="py-4 px-4 font-medium text-slate-400 capitalize">
                        {getCategoryLabel(rec.category)}
                      </td>
                      <td className="py-4 px-4 text-slate-400 font-mono">
                        {rec.period_start === rec.period_end ? (
                          rec.period_start
                        ) : (
                          `${rec.period_start} → ${rec.period_end}`
                        )}
                      </td>
                      <td className="py-4 px-4 text-slate-300 font-mono max-w-[120px] overflow-hidden overflow-ellipsis whitespace-nowrap">
                        {rec.facility_code}
                      </td>
                      <td className="py-4 px-4 text-right font-semibold font-mono text-slate-200">
                        {parseFloat(rec.activity_value).toLocaleString()}
                      </td>
                      <td className="py-4 px-4 font-mono text-slate-400">
                        {rec.activity_unit}
                      </td>
                      <td className="py-4 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-semibold flex items-center w-fit ${stat.badge}`}>
                          {stat.icon}
                          {stat.label}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          {rec.is_locked ? (
                            <Lock className="w-4 h-4 text-slate-500" />
                          ) : (
                            <>
                              <button 
                                onClick={(e) => handleApprove(rec.id, e)}
                                className="p-1 text-slate-400 hover:text-emerald-400 bg-slate-950/20 hover:bg-emerald-500/10 border border-slate-800 rounded transition-colors"
                                title="Approve & Lock Row"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button 
                                onClick={(e) => handleReject(rec.id, e)}
                                className="p-1 text-slate-400 hover:text-rose-400 bg-slate-950/20 hover:bg-rose-500/10 border border-slate-800 rounded transition-colors"
                                title="Reject & Lock Row"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                              <button 
                                onClick={(e) => openFlagModal(rec, e)}
                                className="p-1 text-slate-400 hover:text-orange-400 bg-slate-950/20 hover:bg-orange-500/10 border border-slate-800 rounded transition-colors"
                                title="Flag Row Suspicious"
                              >
                                <Flag className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-slate-800 bg-slate-950/10 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing Page <strong>{page}</strong> of <strong>{totalPages}</strong> (Total: {count} records)
            </span>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setPage(p => Math.max(p - 1, 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button 
                onClick={() => setPage(p => Math.min(p + 1, totalPages))}
                disabled={page === totalPages}
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Flag Dialog Modal */}
      {flaggingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs">
          <form 
            onSubmit={handleFlagSubmit}
            className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl transform transition-all animate-scale-up"
          >
            <div>
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Flag className="w-5 h-5 text-orange-500" />
                Flag Activity Record
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Provide a reason explaining why this data row is marked suspicious. The record will remain unlocked for editing.
              </p>
            </div>

            {flagError && (
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg text-xs">
                {flagError}
              </div>
            )}

            <div>
              <label className="text-[10px] text-slate-500 uppercase tracking-widest block mb-1">Flagging Description</label>
              <textarea 
                value={flagReason}
                onChange={(e) => setFlagReason(e.target.value)}
                placeholder="e.g. Activity value is 4x higher than prior month baseline. Need utility portal review."
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 p-2.5 rounded-xl text-slate-200 text-xs focus:border-brand-500 focus:outline-none font-sans"
              />
            </div>

            <div className="flex justify-end gap-3 text-xs font-semibold pt-2">
              <button 
                type="button"
                onClick={() => setFlaggingRecord(null)}
                className="px-4 py-2 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit"
                className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-slate-950 rounded-xl transition-colors"
              >
                Flag Record
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Record details Audit timeline sidebar/modal */}
      {selectedRecord && (
        <AuditTrailModal 
          record={selectedRecord} 
          onClose={() => setSelectedRecord(null)}
          onRecordUpdated={updateRecordInState}
        />
      )}

    </div>
  );
}
