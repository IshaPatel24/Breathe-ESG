import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, XCircle, ArrowRight } from 'lucide-react';
import { apiRequest, API_BASE, DEFAULT_TENANT } from '../api';

export default function UploadPage() {
  const [uploading, setUploading] = useState(null); // 'SAP' | 'UTILITY' | 'TRAVEL' | null
  const [result, setResult] = useState(null); // parsed batch outcome
  const [errors, setErrors] = useState([]); // error logs for batch
  const [errorText, setErrorText] = useState(null); // global UI error

  async function handleFileUpload(sourceType, file) {
    if (!file) return;

    setUploading(sourceType);
    setResult(null);
    setErrors([]);
    setErrorText(null);

    const formData = new FormData();
    formData.append('source_type', sourceType);
    formData.append('file', file);
    formData.append('tenant_id', DEFAULT_TENANT.slug);

    try {
      const response = await fetch(`${API_BASE}/api/ingestion/upload/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token f8df9911f1c56734ef297ada95eda525128b5c15`,
          'X-Tenant-Slug': DEFAULT_TENANT.slug
        },
        body: formData
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Upload failed');
      }

      setResult(data);

      // If there are errors, fetch them
      if (data.error_count > 0 && data.batch_id) {
        fetchBatchErrors(data.batch_id);
      }

    } catch (err) {
      setErrorText(err.message);
    } finally {
      setUploading(null);
    }
  }

  async function fetchBatchErrors(batchId) {
    try {
      const errData = await apiRequest(`/api/batches/${batchId}/errors/`);
      setErrors(errData);
    } catch (err) {
      console.error("Failed to load batch errors:", err);
    }
  }

  const sourcesConfig = {
    SAP: {
      title: 'SAP Ingestion',
      subtitle: 'Flat file ERP export (German fields, decimal commas)',
      sampleFile: 'sap_seed.csv',
      accepts: '.csv,.txt'
    },
    UTILITY: {
      title: 'Utility Portals Ingestion',
      subtitle: 'Electricity billing exports (MWh/kWh/kVAh, cumulative meter delta)',
      sampleFile: 'utility_seed.csv',
      accepts: '.csv'
    },
    TRAVEL: {
      title: 'Corporate Travel Ingestion',
      subtitle: 'Concur/Navan exports (IATA route coordinates, anonymized PII)',
      sampleFile: 'travel_seed.csv',
      accepts: '.csv'
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Introduction Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">Data Ingestion Center</h1>
        <p className="text-slate-400 mt-2 max-w-xl text-sm leading-relaxed">
          Upload activity files from SAP, Utility providers, and travel managers. Files are normalized, mapped, and audited instantly.
        </p>
      </div>

      {/* Global Error Alert */}
      {errorText && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl flex items-center gap-3 text-sm">
          <XCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorText}</span>
        </div>
      )}

      {/* Upload Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(sourcesConfig).map(([key, config]) => {
          const isCurrentUploading = uploading === key;
          
          return (
            <div key={key} className="glass-card rounded-2xl p-6 flex flex-col justify-between h-[280px]">
              <div>
                <h3 className="text-lg font-bold text-slate-200">{config.title}</h3>
                <p className="text-slate-400 text-xs mt-1 leading-relaxed">{config.subtitle}</p>
                <div className="mt-4">
                  <span className="text-[10px] text-brand-500 uppercase tracking-widest font-bold">Expects:</span>
                  <code className="text-xs text-slate-300 block font-mono mt-1 bg-slate-900/50 p-1.5 rounded border border-slate-800/40">
                    {config.accepts}
                  </code>
                </div>
              </div>
              
              <div className="mt-6">
                <label className={`w-full flex flex-col items-center justify-center py-4 px-3 border border-dashed rounded-xl cursor-pointer transition-all duration-200 ${
                  isCurrentUploading 
                    ? 'border-brand-500/50 bg-brand-500/5 pointer-events-none'
                    : 'border-slate-700 hover:border-brand-500/60 bg-slate-950/20 hover:bg-slate-950/40'
                }`}>
                  {isCurrentUploading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-xs text-brand-400 font-semibold">Processing...</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-slate-400 hover:text-slate-200">
                      <Upload className="w-4 h-4 text-brand-500" />
                      <span className="text-xs font-semibold">Upload File</span>
                    </div>
                  )}
                  <input
                    type="file"
                    className="hidden"
                    accept={config.accepts}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileUpload(key, e.target.files[0]);
                      }
                    }}
                    disabled={uploading !== null}
                  />
                </label>
                <span className="text-[10px] text-slate-500 text-center block mt-2">
                  Seed file: <code className="text-slate-400 font-mono">{config.sampleFile}</code>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Parse Ingestion Results */}
      {result && (
        <div className={`p-6 rounded-2xl border transition-all animate-fade-in ${
          result.error_count > 0 && result.error_count === result.row_count
            ? 'bg-rose-500/5 border-rose-500/20'
            : result.error_count > 0
              ? 'bg-orange-500/5 border-orange-500/20'
              : 'bg-emerald-500/5 border-emerald-500/20'
        }`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {result.error_count > 0 && result.error_count === result.row_count ? (
                <XCircle className="w-8 h-8 text-rose-500" />
              ) : result.error_count > 0 ? (
                <AlertTriangle className="w-8 h-8 text-orange-500" />
              ) : (
                <CheckCircle className="w-8 h-8 text-emerald-500" />
              )}
              <div>
                <h3 className="text-lg font-bold text-slate-200">
                  Ingestion Inbound Batch Summary
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {result.batch_id}</p>
              </div>
            </div>
            <span className={`px-2.5 py-1 text-xs font-bold rounded border ${
              result.status === 'DONE' 
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
            }`}>{result.status}</span>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase">Rows Analyzed</span>
              <p className="text-2xl font-bold text-slate-200 mt-1">{result.row_count}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase">Successful Ingests</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">
                {result.row_count - result.error_count}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase">Rows Failed</span>
              <p className={`text-2xl font-bold mt-1 ${result.error_count > 0 ? 'text-orange-500' : 'text-slate-500'}`}>
                {result.error_count}
              </p>
            </div>
          </div>

          {result.notes && (
            <p className="text-sm text-slate-300 mt-4 bg-slate-900/30 p-3 rounded-lg border border-slate-800/40">
              {result.notes}
            </p>
          )}

          {/* Details of row errors */}
          {errors.length > 0 && (
            <div className="mt-8 space-y-3">
              <h4 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
                Detailed Parser Validation Errors
              </h4>
              <div className="border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold">
                      <th className="py-2.5 px-4 w-[80px]">Row #</th>
                      <th className="py-2.5 px-4 w-[250px]">Raw Source Data</th>
                      <th className="py-2.5 px-4">Parser Exception Message</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-900/20">
                    {errors.map((err) => (
                      <tr key={err.id} className="hover:bg-slate-950/40 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-orange-400">{err.row_number}</td>
                        <td className="py-3 px-4">
                          <pre className="font-mono text-[10px] text-slate-400 max-h-[80px] overflow-y-auto whitespace-pre-wrap">
                            {JSON.stringify(err.raw_row)}
                          </pre>
                        </td>
                        <td className="py-3 px-4 font-mono text-rose-400">{err.error_message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
