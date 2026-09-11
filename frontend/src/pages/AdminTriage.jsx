import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ShieldAlert, ArrowLeft, RefreshCw, X, AlertTriangle, CheckCircle2, Archive, Clock, Truck } from 'lucide-react';
import { DateStrip, toDayKey } from '../components/DateStrip';

const formatDateTime = (dateString) => {
  if (!dateString) return 'Just now';

  const d = new Date(dateString);

  if (isNaN(d.getTime())) return 'Just now';

  const now = new Date();
  const diffInSeconds = Math.floor((now - d) / 1000);

  if (diffInSeconds < 60) {
    return 'Just now';
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60);

  if (diffInMinutes < 60) {
    return `${diffInMinutes} min ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);

  if (diffInHours < 24) {
    return `${diffInHours} hr ago`;
  }

  return d.toLocaleDateString('en-IN', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};
const formatTime = (dateString) => {
  if (!dateString) return 'Unknown time';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return 'Unknown time';
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
};

export default function AdminTriage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState(null);
  const [actionTaken, setActionTaken] = useState(false);
  const [actionError, setActionError] = useState(null);

  const [activeTab, setActiveTab] = useState('active'); // 'active', 'dispatched', or 'archived'
  const [selectedDate, setSelectedDate] = useState(null); // null = "All dates"
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

  const handleAction = async () => {
    const isPrecursor = selectedReport.is_sif_precursor || selectedReport.is_sif;
    const newStatus = isPrecursor ? 'dispatched' : 'archived';

    setActionError(null);
    try {
      await api.updateReportStatus(selectedReport.report_id, newStatus);
      setActionTaken(true);
      setTimeout(() => {
        fetchReports(0); // re-pull from the server — it's the source of truth now
        setSelectedReport(null);
        setActionTaken(false);
      }, 1000);
    } catch (err) {
      console.error('Failed to update status:', err);
      setActionError('Could not save this action. Please try again.');
    }
  };

  const displayedReports = reports.filter((report) => {
    const status = report.status || 'active';
    if (status !== activeTab) return false;
   if (selectedDate && toDayKey(report.report_date) !== selectedDate) return false;
    return true;

  });

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] p-3 sm:p-6 md:p-8 relative">
      <div className="max-w-6xl mx-auto flex flex-wrap justify-between items-center gap-3 mb-4 md:mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <Link to="/" className="shrink-0 p-2 bg-white border border-[var(--border)] rounded-md hover:border-[var(--accent)] transition-colors">
            <ArrowLeft className="w-5 h-5 text-[var(--accent)]" />
          </Link>
          <div className="min-w-0">
            <h1 className="text-base sm:text-lg md:text-xl font-bold truncate">Safety Admin Triage Queue</h1>
            <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-[var(--danger)] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--danger)]" />
              {displayedReports.filter(r => (r.status || 'active') === 'active').length || reports.filter(r => (r.status || 'active') === 'active').length} Active Unreviewed
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <Link to="/admin/dashboard" className="px-3 md:px-4 py-2 bg-[var(--accent-dark)] text-white rounded-md text-xs md:text-sm font-semibold hover:bg-[var(--ink)] transition-colors whitespace-nowrap">
            <span className="hidden sm:inline">Analytics Hub </span>→
          </Link>
          <button onClick={() => fetchReports(0)} className="shrink-0 p-2 bg-white border border-[var(--border)] rounded-md hover:border-[var(--accent)] transition-colors">
            <RefreshCw className={`w-5 h-5 text-[var(--accent)] ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto bg-white rounded-lg border border-[var(--border)] overflow-hidden">
        <div className="p-4 sm:p-6 border-b border-[var(--border)] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm sm:text-base font-bold">Incident Reports</h2>
            <p className="text-[11px] sm:text-xs text-[var(--ink-soft)]">Sorted by Severity, then by Newest.</p>
          </div>

          {/* 3-Tab Switcher */}
          <div className="flex items-center bg-[var(--bg)] border border-[var(--border)] p-1 rounded-md overflow-x-auto max-w-full">
            <button
              onClick={() => setActiveTab('active')}
              className={`shrink-0 px-3 md:px-4 py-1.5 rounded text-[11px] md:text-xs font-bold uppercase tracking-wide transition-all whitespace-nowrap ${activeTab === 'active' ? 'bg-white text-[var(--danger)] shadow-sm border border-[var(--border)]' : 'text-[var(--ink-soft)] hover:text-[var(--ink)]'}`}
            >
              Active Alerts
            </button>
            <button
              onClick={() => setActiveTab('dispatched')}
              className={`shrink-0 px-3 md:px-4 py-1.5 rounded text-[11px] md:text-xs font-bold uppercase tracking-wide transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'dispatched' ? 'bg-white text-blue-700 shadow-sm border border-[var(--border)]' : 'text-[var(--ink-soft)] hover:text-[var(--ink)]'}`}
            >
              <Truck className="w-3.5 h-3.5 shrink-0" /> Dispatched
            </button>
            <button
              onClick={() => setActiveTab('archived')}
              className={`shrink-0 px-3 md:px-4 py-1.5 rounded text-[11px] md:text-xs font-bold uppercase tracking-wide transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'archived' ? 'bg-white text-[var(--ink)] shadow-sm border border-[var(--border)]' : 'text-[var(--ink-soft)] hover:text-[var(--ink)]'}`}
            >
              <Archive className="w-3.5 h-3.5 shrink-0" /> Archived
            </button>
          </div>
        </div>
        <div className="px-4 sm:px-6 pt-4">
          <DateStrip reports={reports} selectedDate={selectedDate} onSelectDate={setSelectedDate} />
        </div>

        {/* Empty / loading state, shared by both layouts */}
        {(loading && displayedReports.length === 0) || displayedReports.length === 0 ? (
          <div className="py-12 px-6 text-center text-sm text-[var(--ink-soft)] font-medium">
            {loading && displayedReports.length === 0 ? 'Loading live data...' : (
              <>
                {activeTab === 'active' && '🎉 No active hazards! Queue is clear.'}
                {activeTab === 'dispatched' && 'No teams have been dispatched yet.'}
                {activeTab === 'archived' && 'No routine reports have been archived yet.'}
              </>
            )}
          </div>
        ) : (
          <>
            {/* Mobile card list - shown below md breakpoint */}
            <div className="md:hidden divide-y divide-[var(--border)]">
              {displayedReports.map((report, idx) => {
                const isPrecursor = report.is_sif_precursor || report.is_sif;
                const severityScore = report.severity_score || report.severity || 0;
                const status = report.status || 'active';

                return (
                  <button
                    key={report.report_id || report.id || idx}
                    onClick={() => { setSelectedReport(report); setActionTaken(false); setActionError(null); }}
                    className={`w-full text-left p-4 flex flex-col gap-2 active:bg-[var(--bg)] ${isPrecursor && status === 'active' ? 'bg-[var(--danger-bg)]/40' : ''}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--ink-soft)]">
                        <Clock className="w-3.5 h-3.5 opacity-70 shrink-0" />
                        {formatDateTime(report.report_date)}
                      </span>
                      <span className={`shrink-0 inline-block px-2 py-0.5 rounded text-[11px] font-bold ${severityScore >= 4 ? 'bg-[var(--danger-bg)] text-[var(--danger)]' : 'bg-[var(--bg)] text-[var(--ink-soft)]'}`}>
                        Level {severityScore}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-[var(--ink)] line-clamp-2">
                      {report.report_text || report.text || 'No description provided'}
                    </p>
                    <div>
                      {status === 'dispatched' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-100"><Truck className="w-3.5 h-3.5" /> Dispatched</span>
                      ) : status === 'archived' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-[var(--bg)] text-[var(--ink-soft)] border border-[var(--border)]"><Archive className="w-3.5 h-3.5" /> Archived</span>
                      ) : isPrecursor ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-[var(--danger)] text-white"><ShieldAlert className="w-3.5 h-3.5" /> SIF Precursor</span>
                      ) : (
                        <span className="text-[11px] font-medium text-[var(--ink-soft)] opacity-70">Routine</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Table layout - shown at md and above */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[var(--bg)] text-[var(--ink-soft)] text-[11px] uppercase tracking-wider border-b border-[var(--border)]">
                    <th className="py-3.5 px-6 font-semibold flex items-center gap-1.5"><Clock className="w-3.5 h-3.5 opacity-70" /> Date & Time</th>
                    <th className="py-3.5 px-6 font-semibold">Incident Details</th>
                    <th className="py-3.5 px-6 font-semibold">Severity</th>
                    <th className="py-3.5 px-6 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] text-sm">
                  {displayedReports.map((report, idx) => {
                    const isPrecursor = report.is_sif_precursor || report.is_sif;
                    const severityScore = report.severity_score || report.severity || 0;
                    const status = report.status || 'active';

                    return (
                      <tr
                        key={report.report_id || report.id || idx}
                        onClick={() => { setSelectedReport(report); setActionTaken(false); setActionError(null); }}
                        className={`transition-colors cursor-pointer hover:bg-[var(--bg)] ${isPrecursor && status === 'active' ? 'bg-[var(--danger-bg)]/30' : ''}`}
                      >
                        <td className="py-4 px-6 text-[var(--ink-soft)] font-medium whitespace-nowrap">
                          {formatDateTime(report.report_date)}
                        </td>
                        <td className="py-4 px-6 font-medium text-[var(--ink)] max-w-sm truncate">
                          {report.report_text || report.text || 'No description provided'}
                        </td>
                        <td className="py-4 px-6">
                          <span className={`inline-block px-2.5 py-1 rounded text-xs font-bold ${severityScore >= 4 ? 'bg-[var(--danger-bg)] text-[var(--danger)]' : 'bg-[var(--bg)] text-[var(--ink-soft)]'}`}>
                            Level {severityScore}
                          </span>
                        </td>
                        <td className="py-4 px-6">
                          {status === 'dispatched' ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold bg-blue-50 text-blue-700 border border-blue-100"><Truck className="w-3.5 h-3.5" /> Dispatched</span>
                          ) : status === 'archived' ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold bg-[var(--bg)] text-[var(--ink-soft)] border border-[var(--border)]"><Archive className="w-3.5 h-3.5" /> Archived</span>
                          ) : isPrecursor ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold bg-[var(--danger)] text-white"><ShieldAlert className="w-3.5 h-3.5" /> SIF Precursor</span>
                          ) : (
                            <span className="text-xs font-medium text-[var(--ink-soft)] opacity-70">Routine</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Inspection Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center sm:p-4">
          <div className="bg-white rounded-t-2xl sm:rounded-lg p-5 sm:p-6 md:p-8 max-w-2xl w-full max-h-[92vh] overflow-y-auto shadow-2xl relative border border-[var(--border)] animate-in fade-in zoom-in-95 duration-200">
            <button onClick={() => setSelectedReport(null)} className="absolute top-4 right-4 p-2 bg-[var(--bg)] hover:bg-[var(--border)] rounded-md transition-colors">
              <X className="w-5 h-5 text-[var(--ink-soft)]" />
            </button>

            <div className="flex items-center gap-2 mb-1 pr-10">
              <h2 className="text-lg sm:text-xl font-bold">
                {selectedReport.status === 'dispatched' && 'Dispatched Incident Log'}
                {selectedReport.status === 'archived' && 'Archived Incident Log'}
                {(!selectedReport.status || selectedReport.status === 'active') && 'Incident Analysis Report'}
              </h2>
              {(!selectedReport.status || selectedReport.status === 'active') && (selectedReport.is_sif_precursor || selectedReport.is_sif) && (
                <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-[var(--danger)] text-white">SIF Precursor</span>
              )}
            </div>
            <p className="text-xs sm:text-sm text-[var(--ink-soft)] font-medium mb-6 flex items-center gap-2">
              <Clock className="w-3.5 h-3.5" /> Reported at {formatTime(selectedReport.report_date)}
            </p>
            <div className="space-y-5">
              <div>
                <p className="text-[11px] font-semibold text-[var(--ink-soft)] uppercase tracking-wider mb-2">Original Field Report</p>
                <div className="bg-[var(--bg)] p-4 rounded-md border border-[var(--border)] text-[var(--ink)] text-sm sm:text-base leading-relaxed">
                  {selectedReport.report_text || selectedReport.text || 'No text provided.'}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1 bg-[var(--danger-bg)] p-4 rounded-md border border-[var(--danger)]/20">
                  <p className="text-[11px] font-semibold text-[var(--danger)] uppercase tracking-wider mb-1">AI Severity Score</p>
                  <p className="text-2xl sm:text-3xl font-extrabold text-[var(--danger)]">Level {selectedReport.severity_score || selectedReport.severity || 0}</p>
                </div>
                <div className="flex-1 bg-[var(--accent)]/10 p-4 rounded-md border border-[var(--accent)]/20">
                  <p className="text-[11px] font-semibold text-[var(--accent-dark)] uppercase tracking-wider mb-1">SIF Precursor</p>
                  <p className="text-xl sm:text-2xl font-bold text-[var(--ink)]">{(selectedReport.is_sif_precursor || selectedReport.is_sif) ? 'Detected' : 'Negative'}</p>
                </div>
              </div>

              <div>
                <p className="text-[11px] font-semibold text-[var(--ink-soft)] uppercase tracking-wider mb-2">AI Recommended Protocol</p>
                <div className="bg-white p-4 rounded-md border border-[var(--border)] text-[var(--ink)] font-medium text-sm">
                  {selectedReport.recommended_check || selectedReport.action || 'No specific action generated by the AI reasoning engine.'}
                </div>
              </div>

              {actionError && (
                <div className="bg-[var(--danger-bg)] border border-[var(--danger)]/30 text-[var(--danger)] text-sm font-medium rounded-md p-3">
                  {actionError}
                </div>
              )}

              {(!selectedReport.status || selectedReport.status === 'active') && (
                <div className="pt-4 border-t border-[var(--border)] flex justify-end">
                  <button
                    onClick={handleAction}
                    disabled={actionTaken}
                    className={`w-full sm:w-auto justify-center px-6 py-3 rounded-md font-bold text-white transition-all flex items-center gap-2 ${
                      actionTaken
                        ? 'bg-emerald-600 scale-95'
                        : (selectedReport.is_sif_precursor || selectedReport.is_sif)
                          ? 'bg-[var(--danger)] hover:opacity-90'
                          : 'bg-[var(--accent-dark)] hover:bg-[var(--ink)]'
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