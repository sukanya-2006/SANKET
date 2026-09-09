import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ShieldAlert, ArrowLeft, RefreshCw, X, AlertTriangle, CheckCircle2, Archive, Clock, Truck } from 'lucide-react';

const formatDateTime = (dateString) => {
  if (!dateString) return 'Just now';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return 'Just now';
  
  return d.toLocaleDateString('en-IN', {
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit'
  });
};

export default function AdminTriage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState(null);
  const [actionTaken, setActionTaken] = useState(false);
  
  // 3-Tab System State
  const [activeTab, setActiveTab] = useState('active'); // 'active', 'dispatched', or 'archived'
  const [dispatchedIds, setDispatchedIds] = useState([]);
  const [archivedIds, setArchivedIds] = useState([]);

  const fetchReports = async (currentOffset = 0) => {
    setLoading(true);
    try {
      const data = await api.getReports(100, currentOffset);
      const items = Array.isArray(data) ? data : data.items || [];
      
      const sortedReports = items.sort((a, b) => {
        const scoreA = a.severity_score || a.severity || 0;
        const scoreB = b.severity_score || b.severity || 0;
        
        if (scoreB !== scoreA) return scoreB - scoreA;
        
        const dateA = new Date(a.created_at || a.timestamp || 0).getTime();
        const dateB = new Date(b.created_at || b.timestamp || 0).getTime();
        return dateB - dateA;
      });

      setReports(sortedReports);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports(0);
  }, []);

  const handleAction = () => {
    setActionTaken(true);
    setTimeout(() => {
      const uniqueId = selectedReport.id || selectedReport.report_text;
      const isPrecursor = selectedReport.is_sif_precursor || selectedReport.is_sif;
      
      // Route to the correct array based on SIF status
      if (isPrecursor) {
        if (!dispatchedIds.includes(uniqueId)) setDispatchedIds([...dispatchedIds, uniqueId]);
      } else {
        if (!archivedIds.includes(uniqueId)) setArchivedIds([...archivedIds, uniqueId]);
      }
      
      setSelectedReport(null);
      setActionTaken(false);
    }, 1000);
  };

  const displayedReports = reports.filter((report) => {
    const uniqueId = report.id || report.report_text;
    const isDispatched = dispatchedIds.includes(uniqueId);
    const isArchived = archivedIds.includes(uniqueId);
    
    if (activeTab === 'active') return !isDispatched && !isArchived;
    if (activeTab === 'dispatched') return isDispatched;
    if (activeTab === 'archived') return isArchived;
    return false;
  });

  return (
    <div className="min-h-screen bg-[#dce4e1] text-[#2c3e37] p-4 md:p-8 relative">
      <div className="max-w-6xl mx-auto flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 bg-white/80 rounded-xl hover:bg-white transition-colors shadow-sm">
            <ArrowLeft className="w-5 h-5 text-[#354f52]" />
          </Link>
          <h1 className="text-2xl font-bold text-[#2f3e46]">Safety Admin Triage Queue</h1>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/admin/dashboard" className="px-4 py-2 bg-[#354f52] text-white rounded-xl text-sm font-semibold shadow hover:bg-[#2f3e46] transition-colors">
            Analytics Hub →
          </Link>
          <button onClick={() => fetchReports(0)} className="p-2 bg-white/80 rounded-xl hover:bg-white transition-colors shadow-sm">
            <RefreshCw className={`w-5 h-5 text-[#354f52] ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto bg-white/90 backdrop-blur-xl rounded-[2rem] shadow-xl border border-white/50 overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Incident Reports</h2>
            <p className="text-xs text-slate-500">Sorted by Severity, then by Newest.</p>
          </div>
          
          {/* 3-Tab Switcher */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setActiveTab('active')}
              className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'active' ? 'bg-white text-rose-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            >
              Active Alerts
            </button>
            <button
              onClick={() => setActiveTab('dispatched')}
              className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-1.5 ${activeTab === 'dispatched' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            >
              <Truck className="w-4 h-4" /> Dispatched
            </button>
            <button
              onClick={() => setActiveTab('archived')}
              className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-1.5 ${activeTab === 'archived' ? 'bg-white text-slate-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            >
              <Archive className="w-4 h-4" /> Archived
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-100">
                <th className="py-4 px-6 font-semibold">Date & Time</th>
                <th className="py-4 px-6 font-semibold">Incident Details</th>
                <th className="py-4 px-6 font-semibold">Severity</th>
                <th className="py-4 px-6 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {loading && displayedReports.length === 0 ? (
                <tr><td colSpan="4" className="py-12 text-center text-slate-400">Loading live data...</td></tr>
              ) : displayedReports.length === 0 ? (
                <tr><td colSpan="4" className="py-12 text-center text-slate-500 font-medium">
                  {activeTab === 'active' && '🎉 No active hazards! Queue is clear.'}
                  {activeTab === 'dispatched' && 'No teams have been dispatched yet.'}
                  {activeTab === 'archived' && 'No routine reports have been archived yet.'}
                </td></tr>
              ) : (
                displayedReports.map((report, idx) => {
                  const isPrecursor = report.is_sif_precursor || report.is_sif;
                  const severityScore = report.severity_score || report.severity || 0;
                  
                  return (
                    <tr 
                      key={report.id || idx} 
                      onClick={() => { setSelectedReport(report); setActionTaken(false); }}
                      className={`transition-colors cursor-pointer hover:bg-slate-100 ${isPrecursor && activeTab === 'active' ? 'bg-rose-50/30' : ''}`}
                    >
                      <td className="py-4 px-6 text-slate-500 font-medium whitespace-nowrap flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 opacity-70" />
                        {formatDateTime(report.created_at || report.timestamp)}
                      </td>
                      <td className="py-4 px-6 font-medium text-slate-700 max-w-sm truncate">
                        {report.report_text || report.text || 'No description provided'}
                      </td>
                      <td className="py-4 px-6">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold ${severityScore >= 4 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-700'}`}>
                          Level {severityScore}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        {activeTab === 'dispatched' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-700"><Truck className="w-3.5 h-3.5" /> Dispatched</span>
                        ) : activeTab === 'archived' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-200 text-slate-700"><Archive className="w-3.5 h-3.5" /> Archived</span>
                        ) : isPrecursor ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500 text-white shadow-sm"><ShieldAlert className="w-3.5 h-3.5" /> SIF Precursor</span>
                        ) : (
                          <span className="text-xs font-medium text-slate-400">Routine</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspection Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 md:p-8 max-w-2xl w-full shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button onClick={() => setSelectedReport(null)} className="absolute top-4 right-4 p-2 bg-slate-100 hover:bg-slate-200 rounded-full transition-colors">
              <X className="w-5 h-5 text-slate-600" />
            </button>
            
            <h2 className="text-2xl font-bold text-[#2f3e46] mb-2 flex items-center gap-2">
              {activeTab === 'dispatched' && <><Truck className="w-6 h-6 text-blue-500" /> Dispatched Incident Log</>}
              {activeTab === 'archived' && <><Archive className="w-6 h-6 text-slate-500" /> Archived Incident Log</>}
              {activeTab === 'active' && <><AlertTriangle className="w-6 h-6 text-amber-500" /> Incident Analysis Report</>}
            </h2>
            <p className="text-sm text-slate-500 font-medium mb-6 flex items-center gap-2">
               <Clock className="w-4 h-4" /> Reported on {formatDateTime(selectedReport.created_at || selectedReport.timestamp)}
            </p>
            
            <div className="space-y-6">
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Original Field Report</p>
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 text-slate-700 text-base leading-relaxed">
                  {selectedReport.report_text || selectedReport.text || 'No text provided.'}
                </div>
              </div>

              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 bg-rose-50 p-4 rounded-2xl border border-rose-100">
                  <p className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-1">AI Severity Score</p>
                  <p className="text-3xl font-extrabold text-rose-700">Level {selectedReport.severity_score || selectedReport.severity || 0}</p>
                </div>
                <div className="flex-1 bg-[#52796f]/10 p-4 rounded-2xl border border-[#52796f]/20">
                  <p className="text-xs font-semibold text-[#354f52] uppercase tracking-wider mb-1">SIF Precursor</p>
                  <p className="text-2xl font-bold text-[#2f3e46]">{(selectedReport.is_sif_precursor || selectedReport.is_sif) ? 'Detected' : 'Negative'}</p>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">AI Recommended Protocol</p>
                <div className="bg-[#f0f4f3] p-4 rounded-2xl border border-[#cad2c5] text-[#2c3e37] font-medium">
                  {selectedReport.recommended_check || selectedReport.action || 'No specific action generated by the AI reasoning engine.'}
                </div>
              </div>
              
              {activeTab === 'active' && (
                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={handleAction}
                    disabled={actionTaken}
                    className={`px-6 py-3 rounded-xl font-bold text-white transition-all flex items-center gap-2 ${
                      actionTaken 
                        ? 'bg-emerald-500 scale-95' 
                        : (selectedReport.is_sif_precursor || selectedReport.is_sif)
                          ? 'bg-rose-600 hover:bg-rose-700 hover:shadow-lg' 
                          : 'bg-[#354f52] hover:bg-[#2f3e46] hover:shadow-lg' 
                    }`}
                  >
                    {actionTaken ? (
                      <><CheckCircle2 className="w-5 h-5" /> Cleared from Queue!</>
                    ) : (selectedReport.is_sif_precursor || selectedReport.is_sif) ? (
                      'Acknowledge & Dispatch Team'
                    ) : (
                      'Mark as Reviewed & Archive'
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}