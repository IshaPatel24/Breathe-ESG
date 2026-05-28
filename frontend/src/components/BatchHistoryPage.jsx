import React, { useState, useEffect } from 'react';
import { Database, CheckCircle, XCircle, AlertTriangle, FileSpreadsheet, Eye, User, Calendar } from 'lucide-react';
import { apiRequest } from '../api';

export default function BatchHistoryPage({ onNavigateToDashboard }) {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedBatchId, setExpandedBatchId] = useState(null);
  const [batchErrors, setBatchErrors] = useState({});

  useEffect(() => {
    fetchBatches();
  }, []);

  async function fetchBatches() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest('/api/batches/');
      setBatches(data.results || data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function toggleExpandBatch(batchId) {
    if (expandedBatchId === batchId) {
      setExpandedBatchId(null);
      return;
    }

    setExpandedBatchId(batchId);
    
    // Load batch errors if not already loaded
    if (!batchErrors[batchId]) {
      try {
        const errors = await apiRequest(`/api/batches/${batchId}/errors/`);
        setBatchErrors(prev => ({
          ...prev,
          [batchId]: errors
        }));
      } catch (err) {
        console.error("Failed to load batch errors:", err);
      }
    }
  }

  if (loading && batches.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm text-slate-400 mt-4 font-semibold">Loading Ingestion Batches...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-sm animate-fade-in">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">Ingestion Batch History</h1>
        <p className="text-slate-400 mt-2 max-w-xl text-sm leading-relaxed">
          Monitor recent raw file uploads, audit processing logs, and check batch conversion statistics.
        </p>
      </div>

      {batches.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center text-slate-500">
          <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-base font-semibold">No Ingestion Batches Found</p>
          <p className="text-xs text-slate-600 mt-1">Upload a seed file to get started.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {batches.map((batch) => {
            const isExpanded = expandedBatchId === batch.id;
            const uploadDate = new Date(batch.uploaded_at).toLocaleString();
            const errorsList = batchErrors[batch.id] || [];
            
            return (
              <div 
                key={batch.id} 
                className={`glass border rounded-2xl overflow-hidden transition-all duration-200 ${
                  isExpanded ? 'border-brand-500/30 ring-1 ring-brand-500/10' : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                
                {/* Header row */}
                <div 
                  onClick={() => toggleExpandBatch(batch.id)}
                  className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 cursor-pointer hover:bg-slate-950/20 transition-colors"
                >
                  
                  <div className="flex items-center gap-3">
                    <span className={`p-2 rounded-lg ${
                      batch.status === 'DONE' 
                        ? 'bg-emerald-500/10 text-emerald-400' 
                        : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      {batch.status === 'DONE' ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                    </span>
                    <div>
                      <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                        {batch.file_name}
                        <span className="px-1.5 py-0.5 text-[9px] font-bold bg-slate-800 text-slate-400 rounded">
                          {batch.data_source ? batch.data_source.source_type : 'SOURCE'}
                        </span>
                      </h3>
                      <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-600" />
                          {uploadDate}
                        </span>
                        <span className="flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-slate-600" />
                          {batch.uploaded_by ? batch.uploaded_by.username : 'System'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right text-xs">
                      <span className="text-slate-500 uppercase tracking-widest text-[9px] block">Conversion</span>
                      <span className="font-semibold text-slate-300">
                        {batch.row_count - batch.error_count} / {batch.row_count} rows
                      </span>
                    </div>
                    
                    {batch.error_count > 0 && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        {batch.error_count} errors
                      </span>
                    )}

                    <button 
                      className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors ${
                        isExpanded
                          ? 'bg-slate-800 border-slate-700 text-slate-100'
                          : 'bg-transparent border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {isExpanded ? 'Hide Details' : 'Details'}
                    </button>
                  </div>

                </div>

                {/* Expanded Details Panel */}
                {isExpanded && (
                  <div className="p-6 bg-slate-950/40 border-t border-slate-850 space-y-6 animate-slide-in">
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase">Batch ID</span>
                        <code className="text-xs text-slate-300 font-mono block mt-1 overflow-hidden overflow-ellipsis">{batch.id}</code>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase">Total Rows</span>
                        <p className="text-lg font-bold text-slate-300 mt-0.5">{batch.row_count}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase">Ingested Records</span>
                        <p className="text-lg font-bold text-emerald-400 mt-0.5">{batch.row_count - batch.error_count}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase">Error Rows</span>
                        <p className="text-lg font-bold text-rose-400 mt-0.5">{batch.error_count}</p>
                      </div>
                    </div>

                    {batch.notes && (
                      <div className="p-3 bg-slate-900/30 border border-slate-850 rounded-lg text-xs text-slate-300 leading-relaxed font-mono">
                        {batch.notes}
                      </div>
                    )}

                    <div className="flex justify-start gap-4">
                      {batch.row_count - batch.error_count > 0 && (
                        <button 
                          onClick={() => onNavigateToDashboard(batch.id)}
                          className="flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-brand-500 hover:bg-brand-600 text-slate-950 rounded-xl transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                          View Ingested Records
                        </button>
                      )}
                    </div>

                    {/* Batch Ingestion Errors Detail list */}
                    {batch.error_count > 0 && (
                      <div className="space-y-3 pt-4 border-t border-slate-850">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                          Batch Parser Validation Errors
                        </h4>
                        {errorsList.length === 0 ? (
                          <div className="text-xs text-slate-500">Loading errors list...</div>
                        ) : (
                          <div className="border border-slate-850 rounded-xl overflow-hidden">
                            <table className="w-full text-left border-collapse text-xs">
                              <thead>
                                <tr className="bg-slate-950/80 border-b border-slate-850 text-slate-400 font-semibold">
                                  <th className="py-2.5 px-4 w-[80px]">Row #</th>
                                  <th className="py-2.5 px-4 w-[200px]">Raw Row</th>
                                  <th className="py-2.5 px-4">Error Context</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-850 bg-slate-900/10">
                                {errorsList.map((err) => (
                                  <tr key={err.id} className="hover:bg-slate-950/40 transition-colors">
                                    <td className="py-3 px-4 font-mono font-bold text-orange-400">{err.row_number}</td>
                                    <td className="py-3 px-4">
                                      <pre className="font-mono text-[10px] text-slate-500 max-h-[80px] overflow-y-auto whitespace-pre-wrap">
                                        {JSON.stringify(err.raw_row)}
                                      </pre>
                                    </td>
                                    <td className="py-3 px-4 font-mono text-rose-450">{err.error_message}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
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
