
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ShieldAlert, ArrowLeft, RefreshCw, X, AlertTriangle, CheckCircle2, Archive, Clock, Truck } from 'lucide-react';

// const formatDateTime = (dateString) => {
//   if (!dateString) return 'Just now';
//   const d = new Date(dateString);
//   if (isNaN(d.getTime())) return 'Just now';
  
//   return d.toLocaleDateString('en-IN', {
//     month: 'short', 
//     day: 'numeric', 
//     hour: '2-digit', 
//     minute: '2-digit'
//   });
// };


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

// The /reports endpoint caps limit at 100, so the queue arrives a page at a time.
const PAGE_SIZE = 100;

// An unclassified report has no score at all. Coercing that missing value to 0 printed it as
// "Level 0" - the same badge a genuinely harmless report gets - so a report the classifier had
// never seen read as a confident all-clear.
const severityOf = (report) => {
  const raw = report.severity_score ?? report.severity;

  if (raw === null || raw === undefined || raw === '') return null;

  const score = Number(raw);

  return Number.isNaN(score) ? null : score;
};

// Highest severity first, then newest - applied to the whole accumulated list rather than to a
// single page, so "load more" cannot strand a Level 5 below a Level 1.
const sortBySeverityThenNewest = (items) =>
  [...items].sort((a, b) => {
    const severityA = severityOf(a) ?? 0;
    const severityB = severityOf(b) ?? 0;

    // Higher severity first
    if (severityB !== severityA) {
      return severityB - severityA;
    }

    // Newest first
    const dateA = new Date(
      a.created_at || a.report_date || 0
    ).getTime();

    const dateB = new Date(
      b.created_at || b.report_date || 0
    ).getTime();

    return dateB - dateA;
  });

export default function AdminTriage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState(null);
  const [actionTaken, setActionTaken] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(null);

  const [activeTab, setActiveTab] = useState('active'); // 'active', 'dispatched', or 'archived'
  const [dayFilter, setDayFilter] = useState('');

  // const fetchReports = async (currentOffset = 0) => {
  //   setLoading(true);
  //   try {
  //     const data = await api.getReports(100, currentOffset);
  //     const items = Array.isArray(data) ? data : data.items || [];

  //     const sortedReports = items.sort((a, b) => {
  //       const scoreA = a.severity_score || a.severity || 0;
  //       const scoreB = b.severity_score || b.severity || 0;

  //       if (scoreB !== scoreA) return scoreB - scoreA;

  //       const dateA = new Date(a.created_at || a.timestamp || 0).getTime();
  //       const dateB = new Date(b.created_at || b.timestamp || 0).getTime();
  //       return dateB - dateA;
  //     });

  //     setReports(sortedReports);
  //   } catch (err) {
  //     console.error('Failed to load reports:', err);
  //   } finally {
  //     setLoading(false);
  //   }
  // };


  const fetchReports = async (currentOffset = 0) => {
    setLoading(true);

    try {
      const data = await api.getReports(PAGE_SIZE, currentOffset, {
        status: activeTab,
        reportDate: dayFilter || undefined,
      });

      const items = Array.isArray(data)
        ? data
        : data.items || [];

      // The queue is one page of a much bigger table. Throwing away data.total made the first
      // page look like the whole queue, so a report submitted a minute ago could sit unseen at
      // offset 100 with nothing on screen to say more rows existed.
      setTotal(
        typeof data.total === 'number' ? data.total : null
      );

      // offset 0 is a fresh load or a refresh; anything else is "load more" and appends.
      setReports((prev) =>
        sortBySeverityThenNewest(
          currentOffset === 0 ? items : [...prev, ...items]
        )
      );

      setError(null);

    } catch (err) {
      console.error(
        'Failed to load live reports:',
        err
      );

      // Never blank the queue on failure. A cold backend start, a CORS rejection or a dropped
      // connection used to leave an empty list, and an empty list renders as
      // "No active hazards! Queue is clear." - the exact opposite of what happened, told to
      // the one person whose job is to act on the hazards.
      setError(err.message || 'Could not reach the API.');

    } finally {
      setLoading(false);
    }
  };

    // Changing tab or day is a new query, not a filter over what is already loaded, so the
  // offset has to reset or page 2 of `active` becomes page 2 of `archived`.
  useEffect(() => {
    setReports([]);
    setTotal(null);
    fetchReports(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, dayFilter]);


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

  // The server already scoped this page to the active tab, so there is nothing left to
  // filter here. Re-filtering would silently drop rows whose status changed between the
  // fetch and the render.
  const displayedReports = reports;

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
            {/* One day at a time, with the risk ranking intact inside the day. This is the
                day-wise view - the queue itself stays sorted by risk, because 209 reports
                span 101 dates and 60 of those hold a single report. */}
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-lg font-bold text-slate-800">Incident Reports</h2>
              <input
                type="date"
                value={dayFilter}
                onChange={(e) => setDayFilter(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-2 py-1 text-slate-600"
                title="Show a single day, worst first"
              />
              {dayFilter && (
                <button
                  onClick={() => setDayFilter('')}
                  className="text-xs font-semibold text-slate-500 hover:text-slate-700 underline"
                >
                  clear
                </button>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Sorted by Severity, then by Newest.
              {total !== null && ` Showing ${reports.length} of ${total}${dayFilter ? ` on ${dayFilter}` : ''}.`}
            </p>
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

        {error && (
          <div className="mx-6 mt-6 bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-slate-800 mb-0.5">Could not load the triage queue</p>
              <p className="text-sm text-slate-600 mb-3">{error}</p>
              <button
                onClick={() => fetchReports(0)}
                className="text-xs font-semibold text-[#354f52] bg-[#52796f]/10 px-3 py-1.5 rounded-xl hover:bg-[#52796f]/20 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        )}

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
                  {/* An empty list after a failed fetch is not an empty queue, so say nothing
                      reassuring until the queue has actually been seen. */}
                  {error ? 'The queue could not be loaded.' : (
                    <>
                      {activeTab === 'active' && '🎉 No active hazards! Queue is clear.'}
                      {activeTab === 'dispatched' && 'No teams have been dispatched yet.'}
                      {activeTab === 'archived' && 'No routine reports have been archived yet.'}
                    </>
                  )}
                </td></tr>
              ) : (
                displayedReports.map((report, idx) => {
                  const isPrecursor = report.is_sif_precursor || report.is_sif;
                  const severityScore = severityOf(report);
                  const status = report.status || 'active';

                  return (
                    <tr
                      key={report.report_id || report.id || idx}
                      onClick={() => { setSelectedReport(report); setActionTaken(false); setActionError(null); }}
                      className={`transition-colors cursor-pointer hover:bg-slate-100 ${isPrecursor && status === 'active' ? 'bg-rose-50/30' : ''}`}
                    >
                      <td className="py-4 px-6 text-slate-500 font-medium whitespace-nowrap flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 opacity-70" />
                        {/* {formatDateTime(
                       report.created_at ||
                       report.report_date ||
                         report.timestamp
                       )} */}

                       {formatDateTime(report.created_at)}
                      </td>
                      <td className="py-4 px-6 font-medium text-slate-700 max-w-sm truncate">
                        {report.report_text || report.text || 'No description provided'}
                      </td>
                      <td className="py-4 px-6">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold ${severityScore >= 4 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-700'}`}>
                          {severityScore === null ? 'Unclassified' : `Level ${severityScore}`}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        {status === 'dispatched' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-700"><Truck className="w-3.5 h-3.5" /> Dispatched</span>
                        ) : status === 'archived' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-200 text-slate-700"><Archive className="w-3.5 h-3.5" /> Archived</span>
                        ) : isPrecursor ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500 text-white shadow-sm"><ShieldAlert className="w-3.5 h-3.5" /> SIF Precursor</span>
                        ) : severityScore === null ? (
                          <span className="text-xs font-medium text-slate-400">Unclassified</span>
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

        {/* Without this the screen stopped at the first page and gave no sign there was more,
            so the most natural demo - submit a report, then find it in triage - could fail. */}
        {total !== null && reports.length < total && (
          <div className="p-4 border-t border-slate-100 text-center">
            <button
              onClick={() => fetchReports(reports.length)}
              disabled={loading}
              className="px-4 py-2 bg-[#354f52] text-white rounded-xl text-sm font-semibold shadow hover:bg-[#2f3e46] transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading...' : `Load ${Math.min(PAGE_SIZE, total - reports.length)} more`}
            </button>
          </div>
        )}
      </div>

      {/* Inspection Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 md:p-8 max-w-2xl w-full shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button onClick={() => setSelectedReport(null)} className="absolute top-4 right-4 p-2 bg-slate-100 hover:bg-slate-200 rounded-full transition-colors">
              <X className="w-5 h-5 text-slate-600" />
            </button>

            <h2 className="text-2xl font-bold text-[#2f3e46] mb-2 flex items-center gap-2">
              {selectedReport.status === 'dispatched' && <><Truck className="w-6 h-6 text-blue-500" /> Dispatched Incident Log</>}
              {selectedReport.status === 'archived' && <><Archive className="w-6 h-6 text-slate-500" /> Archived Incident Log</>}
              {(!selectedReport.status || selectedReport.status === 'active') && <><AlertTriangle className="w-6 h-6 text-amber-500" /> Incident Analysis Report</>}
            </h2>
             <p className="text-sm text-slate-500 font-medium mb-6 flex items-center gap-2">
            <Clock className="w-4 h-4" />
                Reported on {formatDateTime(selectedReport.created_at)}
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
                  <p className="text-3xl font-extrabold text-rose-700">
                    {severityOf(selectedReport) === null ? 'Unclassified' : `Level ${severityOf(selectedReport)}`}
                  </p>
                </div>
                <div className="flex-1 bg-[#52796f]/10 p-4 rounded-2xl border border-[#52796f]/20">
                  <p className="text-xs font-semibold text-[#354f52] uppercase tracking-wider mb-1">SIF Precursor</p>
                  <p className="text-2xl font-bold text-[#2f3e46]">{(selectedReport.is_sif_precursor || selectedReport.is_sif) ? 'Detected' : severityOf(selectedReport) === null ? 'Not classified' : 'Negative'}</p>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">AI Recommended Protocol</p>
                <div className="bg-[#f0f4f3] p-4 rounded-2xl border border-[#cad2c5] text-[#2c3e37] font-medium">
                  {selectedReport.recommended_check || selectedReport.action || 'No specific action generated by the AI reasoning engine.'}
                </div>
              </div>

              {actionError && (
                <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm font-medium rounded-xl p-3">
                  {actionError}
                </div>
              )}

              {(!selectedReport.status || selectedReport.status === 'active') && (
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













