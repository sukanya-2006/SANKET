import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { ShieldCheck, HardHat, ClipboardList, ArrowRight } from 'lucide-react';
import WorkerAnalyzer from './pages/WorkerAnalyzer';
import AdminTriage from './pages/AdminTriage';
import AdminDashboard from './pages/AdminDashboard';

function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] flex flex-col items-center justify-center px-4 py-16 sm:py-20">

      {/* Top Tag Pill */}
      <div className="flex items-center gap-2 bg-white px-3 sm:px-4 py-1.5 rounded-md text-[var(--accent)] text-[11px] sm:text-xs font-semibold uppercase tracking-wider mb-6 sm:mb-8 border border-[var(--border)]">
        <ShieldCheck className="w-4 h-4 text-[var(--accent)] shrink-0" />
        <span className="text-center">Oil India Limited • SIF Safety Portal</span>
      </div>

      {/* Hero Content */}
      <h1 className="text-2xl sm:text-4xl md:text-5xl font-extrabold text-center max-w-xl mb-3 sm:mb-4 tracking-tight leading-tight">
        Keeping our field safe, <span className="text-[var(--accent)]">effortlessly.</span>
      </h1>
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
                Offline Ready
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold mb-2">Field Worker Portal</h2>
            <p className="text-[var(--ink-soft)] text-sm leading-relaxed">
              Fast, hands-free field reporting with voice transcription and instant AI triage tips.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-[var(--border)] grid grid-cols-2 gap-3 text-[11px] uppercase tracking-wider text-[var(--ink-soft)]">
            <div>
              <p className="opacity-70 mb-0.5">Reporting Latency</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">~45 Seconds</p>
            </div>
            <div>
              <p className="opacity-70 mb-0.5">Voice Engine</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">Multilingual Sync</p>
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
                3 Precursors
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold mb-2">Safety Admin Hub</h2>
            <p className="text-[var(--ink-soft)] text-sm leading-relaxed">
              Access the prioritized SIF precursor queue, AI reasoning inspections, and site risk analytics.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-[var(--border)] grid grid-cols-2 gap-3 text-[11px] uppercase tracking-wider text-[var(--ink-soft)]">
            <div>
              <p className="opacity-70 mb-0.5">Model Accuracy</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">96.4% Precision</p>
            </div>
            <div>
              <p className="opacity-70 mb-0.5">Triage Stream</p>
              <p className="font-bold text-[var(--ink)] normal-case tracking-normal">Active Telemetry</p>
            </div>
          </div>

          <div className="mt-6 flex items-center gap-2 text-[var(--accent-dark)] text-sm font-bold group-hover:translate-x-1 transition-transform">
            <span>Open Admin Hub</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

      </div>

      {/* Compliance strip */}
      <div className="mt-8 sm:mt-10 flex flex-wrap items-center justify-center gap-2 sm:gap-3 px-2">
        <span className="text-[10px] sm:text-[11px] font-semibold text-[var(--ink-soft)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-md">
          OSHA 1910.119 PSM Compliant
        </span>
        <span className="text-[10px] sm:text-[11px] font-semibold text-[var(--ink-soft)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-md">
          Central SIF Model v4.8 Active
        </span>
        <span className="text-[10px] sm:text-[11px] font-semibold text-[var(--ink-soft)] bg-white border border-[var(--border)] px-3 py-1.5 rounded-md">
          Edge Gateway Synced
        </span>
      </div>

      {/* Footer */}
      <div className="mt-10 sm:mt-14 flex flex-col sm:flex-row items-center gap-1.5 sm:gap-4 text-[var(--ink-soft)] text-[11px] tracking-wide text-center px-4">
        <span>SIH 2026 • Certified Industrial Safety Protocol</span>
        <span className="hidden sm:inline opacity-40">•</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
          14 Active Facilities Monitored
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