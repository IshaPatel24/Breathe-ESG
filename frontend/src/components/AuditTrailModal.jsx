import React, { useState, useEffect } from 'react';
import { X, Clock, FileText, CheckCircle, AlertTriangle, XCircle, ArrowRight, User } from 'lucide-react';
import { apiRequest } from '../api';

export default function AuditTrailModal({ record, onClose, onRecordUpdated }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (record) {
      fetchAuditLogs();
    }
  }, [record]);

  async function fetchAuditLogs() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest(`/api/records/${record.id}/audit-log/`);
      setLogs(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!record) return null;

  // Format Status badge helper
  const getStatusBadge = (status) => {
    const configs = {
      PENDING_REVIEW: { label: 'Pending Review', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
      APPROVED: { label: 'Approved', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
      REJECTED: { label: 'Rejected', color: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
      FLAGGED: { label: 'Flagged', color: 'bg-orange-500/10 text-orange-400 border-orange-500/20' }
    };
    const c = configs[status] || configs.PENDING_REVIEW;
    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${c.color}`}>{c.label}</span>;
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'APPROVED': return <CheckCircle className="w-5 h-5 text-emerald-400" />;
      case 'REJECTED': return <XCircle className="w-5 h-5 text-rose-400" />;
      case 'FLAGGED': return <AlertTriangle className="w-5 h-5 text-orange-400" />;
      case 'EDITED': return <Clock className="w-5 h-5 text-blue-400" />;
      default: return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm transition-opacity duration-300">
      <div className="w-full max-w-2xl h-screen bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col transform transition-transform duration-300 animate-slide-in overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div>
            <span className="text-xs font-semibold text-brand-500 uppercase tracking-wider">{record.source_type} SOURCE RECORD</span>
            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-3 mt-1">
              Record Audit Trail
              {getStatusBadge(record.status)}
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-100 bg-slate-800/40 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Record Summary */}
          <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-950/30 border border-slate-800/50">
            <div>
              <span className="text-xs text-slate-500 uppercase">Scope & Category</span>
              <p className="text-sm font-semibold text-slate-200 mt-0.5">
                {record.scope.replace('_', ' ')} — {record.category.replace('_', ' ')}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-500 uppercase">Activity Value</span>
              <p className="text-sm font-semibold text-slate-200 mt-0.5">
                {parseFloat(record.activity_value).toLocaleString()} {record.activity_unit}
                <span className="text-xs text-slate-500 block">
                  Original: {parseFloat(record.activity_value_original).toLocaleString()} {record.activity_unit_original}
                </span>
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-500 uppercase">Period (Start - End)</span>
              <p className="text-sm font-semibold text-slate-200 mt-0.5">
                {record.period_start} to {record.period_end}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-500 uppercase">Facility / Site Code</span>
              <p className="text-sm font-semibold text-slate-200 mt-0.5">
                {record.facility_code}
              </p>
            </div>
            {record.flag_reason && (
              <div className="col-span-2 p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                <span className="text-xs text-orange-400 font-semibold block uppercase">Flag Reason</span>
                <p className="text-sm text-orange-300 mt-0.5">{record.flag_reason}</p>
              </div>
            )}
          </div>

          {/* Audit Logs Timeline */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand-500" />
              Change History
            </h3>
            
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : error ? (
              <div className="p-3 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg text-sm">{error}</div>
            ) : logs.length === 0 ? (
              <div className="text-center py-8 text-sm text-slate-500">No logs found for this record.</div>
            ) : (
              <div className="relative border-l border-slate-800 ml-3 pl-6 space-y-6">
                {logs.map((log) => {
                  const date = new Date(log.changed_at);
                  const formattedDate = date.toLocaleString();
                  const reviewer = log.changed_by_detail ? log.changed_by_detail.username : 'System';
                  
                  return (
                    <div key={log.id} className="relative">
                      {/* Left Dot Icon */}
                      <span className="absolute -left-[37px] top-0 flex items-center justify-center bg-slate-900 border border-slate-800 rounded-full p-1.5 shadow-sm">
                        {getActionIcon(log.action)}
                      </span>
                      
                      <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-4 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span className="flex items-center gap-1.5 font-medium text-slate-200">
                            <User className="w-3.5 h-3.5 text-slate-500" />
                            {reviewer}
                          </span>
                          <span>{formattedDate}</span>
                        </div>
                        <h4 className="text-sm font-semibold text-slate-200">
                          {log.action.replace('_', ' ')}
                        </h4>
                        
                        {/* State diff details */}
                        {log.action !== 'CREATED' && log.before_state && log.after_state && (
                          <div className="text-xs space-y-1 mt-2 p-2 rounded bg-slate-950/40 text-slate-300">
                            {log.before_state.status !== log.after_state.status && (
                              <div className="flex items-center gap-1">
                                <span className="text-slate-500">Status:</span>
                                <span className="line-through text-rose-400">{log.before_state.status}</span>
                                <ArrowRight className="w-3 h-3 text-slate-500" />
                                <span className="text-emerald-400">{log.after_state.status}</span>
                              </div>
                            )}
                            {log.before_state.flag_reason !== log.after_state.flag_reason && (
                              <div>
                                <span className="text-slate-500 block">Flag Reason Changed:</span>
                                {log.before_state.flag_reason && (
                                  <p className="text-rose-400 line-through text-xs font-mono">{log.before_state.flag_reason}</p>
                                )}
                                <p className="text-emerald-400 text-xs font-mono">{log.after_state.flag_reason || '(removed)'}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Raw Verbatim Data */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4 text-brand-500" />
              Verbatim Raw Row (Ingested JSON)
            </h3>
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 overflow-x-auto">
              <pre className="text-xs text-cyan-400 font-mono leading-relaxed">
                {JSON.stringify(record.raw_data, null, 2)}
              </pre>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
