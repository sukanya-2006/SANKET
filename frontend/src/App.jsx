import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { ShieldCheck, HardHat, ClipboardList, ArrowRight } from 'lucide-react';
import { api } from './api';
import WorkerAnalyzer from './pages/WorkerAnalyzer';
import AdminTriage from './pages/AdminTriage';
import AdminDashboard from './pages/AdminDashboard';

// No number on this page is hardcoded, and nothing here claims a certification.
//
// This screen used to open with "96.4% Precision" under the label Model Accuracy, badges reading
// "OSHA 1910.119 PSM Compliant", "Central SIF Model v4.8 Active" and "Edge Gateway Synced", a
// footer claiming "14 Active Facilities Monitored", and an "Offline Ready" pill on the worker
// card. Not one of them came from the code. Measured precision was withdrawn along with the rest of the LLM figures and README.md forbids
// quoting accuracy at all, no compliance assessment was ever run, there is no v4.8 and no edge
// gateway, and the dataset has 8 sites.
//
// "Offline Ready" was the dangerous one. There is no service worker, no navigator.onLine check
// and no submission queue anywhere in frontend/src. A worker who believed that pill would file
// a hazard report into nothing, out in the field, with no signal and no error.
//
// This is also the first screen a judge sees, and it read as an Oil India product rather than
// a prototype built for their problem statement.
//
// So: the stats that remain are fetched, shown next to the sample size they came from, and read
// "—" until they load. Everything else describes what the system actually does.

function LandingPage() {
  const [summary, setSummary] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let cancelled = false;

    // A role picker must still render when the API is down, so a failed fetch leaves the
    // placeholders standing rather than putting an error in front of the two links that are
    // the entire point of the page.
    Promise.all([
      api.getSummary().catch(() => null),
      api.getHealth().catch(() => null)
    ]).then(([summaryData, healthData]) => {
      if (cancelled) return;
      setSummary(summaryData);
      setHealth(healthData);
    });

    return () => { cancelled = true; };
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] flex flex-col items-center justify-center px-4 py-16 sm:py-20">

      {/* Top Tag Pill */}
      <div className="flex items-center gap-2 bg-white px-3 sm:px-4 py-1.5 rounded-md text-[var(--accent)] text-[11px] sm:text-xs font-semibold uppercase tracking-wider mb-6 sm:mb-8 border border-[var(--border)]">
        <ShieldCheck className="w-4 h-4 text-[var(--accent)] shrink-0" />
        <span className="text-center">SIH 2026 Prototype • Built for the Oil India SIF Problem Statement</span>
      </div>

      {/* Hero Content.

          The product name goes here, not just in the browser tab. Every screenshot, every
          screen-share and every photo of the demo crops to this area, and a landing page that
          never says what the thing is called makes the deck and the app look like two
          projects. SANKET is also the word the pitch uses out loud. */}
      <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-center tracking-tight leading-none mb-2">
        SANKET
      </h1>
      <p className="text-[var(--accent)] text-center text-xs sm:text-sm font-semibold uppercase tracking-[0.2em] mb-5 sm:mb-6">
        SIF Precursor Detection
      </p>
      <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-center max-w-xl mb-3 sm:mb-4 tracking-tight leading-tight">
        Keeping our field safe, <span className="text-[var(--accent)]">effortlessly.</span>
      </h2>
      <p className="text-[var(--ink-soft)] text-center max-w-md mb-10 sm:mb-12 text-sm md:text-base leading-relaxed px-2">
        Choose your operational role below to log an active field hazard or access the safety administrative triage and AI reasoning hub.
      </p>

      {/* Role Selection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 w-full max-w-2xl">

        {/* Field Worker Card */}
        <Link
          to="/worker/report"
          className="group bg-white border border-[var(--border)] p-6 sm:p-8 rounded-lg shadow-sm hover:shadow-md hover:border-[var(--accent)]/40 transition-all duration-200 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-start justify-between mb-5 gap-2">
              <div className="w-11 h-11 sm:w-12 sm:h-12 bg-[var(--accent)]/10 text-[var(--accent)] rounded-md flex items-center justify-center group-hover:bg-[var(--accent)] group-hover:text-white transition-all shrink-0">
                <HardHat className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <span className="shrink-0 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider bg-[var(--accent)]/10 text-[var(--accent)] px-2 py-1 rounded">
                Voice or Typed
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold mb-2">Field Worker Portal</h2>
            <p className="text-[var(--ink-soft)] text-sm leading-relaxed">
              Speak or type a hazard in your own language. The report is transcribed, classified, and sent straight to the triage queue.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-[var(--border)] grid grid-cols-2 gap-3 text-[11px] uppercase tracking-wider text-[var(--ink-soft)]">
            <div>
              <p className="opacity-70 mb-0.5">Voice Languages</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">English, Hindi, Odia</p>
            </div>
            <div>
              <p className="opacity-70 mb-0.5">Suggested Check</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">From a Fixed Lookup</p>
            </div>
          </div>

          <div className="mt-6 flex items-center gap-2 text-[var(--accent)] text-sm font-bold group-hover:translate-x-1 transition-transform">
            <span>Open Worker View</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

        {/* Safety Admin Card */}
        <Link
          to="/admin/triage"
          className="group bg-white border border-[var(--border)] p-6 sm:p-8 rounded-lg shadow-sm hover:shadow-md hover:border-[var(--accent-dark)]/40 transition-all duration-200 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-start justify-between mb-5 gap-2">
              <div className="w-11 h-11 sm:w-12 sm:h-12 bg-[var(--accent-dark)]/10 text-[var(--accent-dark)] rounded-md flex items-center justify-center group-hover:bg-[var(--accent-dark)] group-hover:text-white transition-all shrink-0">
                <ClipboardList className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <span className="shrink-0 flex items-center gap-1.5 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider bg-[var(--danger-bg)] text-[var(--danger)] px-2 py-1 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--danger)]" />
                {summary ? `${summary.precursor_count} Precursors` : '— Precursors'}
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold mb-2">Safety Admin Hub</h2>
            <p className="text-[var(--ink-soft)] text-sm leading-relaxed">
              Access the prioritized SIF precursor queue, AI reasoning inspections, and site risk analytics.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-[var(--border)] grid grid-cols-2 gap-3 text-[11px] uppercase tracking-wider text-[var(--ink-soft)]">
            <div>
              {/* The denominator sits beside the precursor count deliberately: a count with no
                  sample size behind it is exactly the kind of number this page used to invent. */}
              <p className="opacity-70 mb-0.5">Reports Classified</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">
                {summary ? summary.total_reports : '—'}
              </p>
            </div>
            <div>
              <p className="opacity-70 mb-0.5">Rubric Version</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">
                {health ? `v${health.rubric_version}` : '—'}
              </p>
            </div>
          </div>

          <div className="mt-6 flex items-center gap-2 text-[var(--accent-dark)] text-sm font-bold group-hover:translate-x-1 transition-transform">
            <span>Open Admin Hub</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

      </div>

      {/* Disclosure strip. What the system is actually running on, in place of the compliance
          and certification badges that no assessment ever backed. */}
      <div className="mt-8 sm:mt-10 flex flex-wrap items-center justify-center gap-2 sm:gap-3 px-2">
        <span className="text-[10px] sm:text-[11px] font-semibold text-[var(--ink-soft)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-md">
          Synthetic and public OSHA data • no Oil India data
        </span>
        <span className="text-[10px] sm:text-[11px] font-semibold text-[var(--ink-soft)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-md">
          Classifier in use: {health ? health.primary_classifier : '—'}
        </span>
        <span className="text-[10px] sm:text-[11px] font-semibold text-[var(--ink-soft)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-md">
          Recommended checks are a fixed lookup, never generated advice
        </span>
      </div>

      {/* Footer */}
      <div className="mt-10 sm:mt-14 flex flex-col sm:flex-row items-center gap-1.5 sm:gap-4 text-[var(--ink-soft)] text-[11px] tracking-wide text-center px-4">
        <span>SIH 2026 entry • a prototype, not a deployed Oil India system</span>
        <span className="hidden sm:inline opacity-40">•</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
          {health
            ? (health.data_source === 'postgres' ? 'Live database' : 'Seeded sample data')
            : 'Checking data source…'}
        </span>
      </div>

    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/worker/report" element={<WorkerAnalyzer />} />
        <Route path="/admin/triage" element={<AdminTriage />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
