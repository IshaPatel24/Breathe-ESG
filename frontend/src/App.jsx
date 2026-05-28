import React, { useState } from 'react';
import { Layout, FileDown, History, BarChart3, CloudLightning, User } from 'lucide-react';
import { DEFAULT_TENANT, CURRENT_USER } from './api';
import UploadPage from './components/UploadPage';
import ReviewDashboard from './components/ReviewDashboard';
import BatchHistoryPage from './components/BatchHistoryPage';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'upload' | 'batches'
  const [activeBatchFilter, setActiveBatchFilter] = useState('');

  return (
    <div className="min-h-screen flex flex-col font-sans">
      
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-900 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          
          {/* Logo Brand */}
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-gradient-to-tr from-brand-600 to-accent-600 rounded-xl shadow-md shadow-brand-500/20">
              <CloudLightning className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <h1 className="text-base font-extrabold text-slate-100 tracking-tight leading-none">Breathe ESG</h1>
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mt-0.5">Ingestor & Auditor</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1.5 text-xs font-semibold">
            <button 
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-200 ${
                activeTab === 'dashboard' 
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20 font-bold' 
                  : 'text-slate-400 hover:text-slate-200 border border-transparent'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              Review Dashboard
            </button>
            <button 
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-200 ${
                activeTab === 'upload' 
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20 font-bold' 
                  : 'text-slate-400 hover:text-slate-200 border border-transparent'
              }`}
            >
              <FileDown className="w-4 h-4" />
              File Ingestion
            </button>
            <button 
              onClick={() => setActiveTab('batches')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-200 ${
                activeTab === 'batches' 
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20 font-bold' 
                  : 'text-slate-400 hover:text-slate-200 border border-transparent'
              }`}
            >
              <History className="w-4 h-4" />
              Batch History
            </button>
          </nav>

          {/* Tenant Selector & User Panel */}
          <div className="flex items-center gap-4 text-xs">
            <div className="text-right hidden sm:block">
              <span className="text-[9px] text-slate-500 block uppercase tracking-wider">Active Tenant</span>
              <span className="font-bold text-slate-350">{DEFAULT_TENANT.name}</span>
            </div>
            <div className="h-8 w-px bg-slate-800 hidden sm:block"></div>
            
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
              <div className="w-5 h-5 rounded-full bg-brand-500/20 flex items-center justify-center">
                <User className="w-3 h-3 text-brand-400" />
              </div>
              <span className="font-medium text-slate-300 capitalize">{CURRENT_USER.username}</span>
            </div>
          </div>

        </div>
      </header>

      {/* Main Page Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {activeTab === 'dashboard' && (
          <ReviewDashboard 
            initialBatchFilter={activeBatchFilter} 
            onClearBatchFilter={() => setActiveBatchFilter('')} 
          />
        )}
        {activeTab === 'upload' && <UploadPage />}
        {activeTab === 'batches' && (
          <BatchHistoryPage 
            onNavigateToDashboard={(batchId) => {
              setActiveBatchFilter(batchId);
              setActiveTab('dashboard');
            }}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-slate-900 text-center text-[10px] text-slate-600 bg-slate-950/20">
        <p>© 2026 Breathe ESG Ingestor. Multi-tenant corporate activity normalization engine.</p>
      </footer>

    </div>
  );
}
