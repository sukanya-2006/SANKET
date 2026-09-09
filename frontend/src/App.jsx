import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { ShieldCheck, HardHat, ClipboardList, ArrowRight } from 'lucide-react';
import WorkerAnalyzer from './pages/WorkerAnalyzer';
import AdminTriage from './pages/AdminTriage';
import AdminDashboard from './pages/AdminDashboard';

function LandingPage() {
  return (
    <div className="min-h-screen bg-[#dce4e1] text-[#2c3e37] flex flex-col items-center justify-center px-4">
      
      {/* Top Tag Pill */}
      <div className="flex items-center gap-2 bg-white/70 backdrop-blur-md px-4 py-1.5 rounded-full text-[#354f52] text-xs font-semibold mb-8 shadow-sm border border-white/50">
        <ShieldCheck className="w-4 h-4 text-[#52796f]" />
        Oil India Limited • SIF Safety Portal
      </div>

      {/* Hero Content */}
      <h1 className="text-4xl md:text-5xl font-extrabold text-center max-w-xl mb-4 tracking-tight text-[#2f3e46]">
        Keeping our field safe, <span className="text-[#52796f]">effortlessly.</span>
      </h1>
      <p className="text-slate-600 text-center max-w-md mb-12 text-sm md:text-base leading-relaxed">
        Choose your portal below to report field incidents or access the safety management analytics hub.
      </p>

      {/* Role Selection Cards (Sage & Minimalist) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl">
        
        {/* Field Worker Card */}
        <Link 
          to="/worker/report"
          className="group bg-white/80 hover:bg-white backdrop-blur-xl border border-white/60 p-8 rounded-xl shadow-xl shadow-slate-400/10 transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 bg-[#52796f]/10 text-[#354f52] rounded-2xl flex items-center justify-center mb-5 group-hover:bg-[#52796f] group-hover:text-white transition-all">
              <HardHat className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-[#2f3e46] mb-2">Field Worker</h2>
            <p className="text-slate-500 text-sm leading-relaxed">
              Quick incident reporting optimized for mobile devices with voice transcription and smart tips.
            </p>
          </div>
          <div className="mt-8 flex items-center gap-2 text-[#354f52] text-sm font-bold group-hover:translate-x-1 transition-transform">
            <span>Open Worker View</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

        {/* Safety Admin Card */}
        <Link 
          to="/admin/triage"
          className="group bg-white/80 hover:bg-white backdrop-blur-xl border border-white/60 p-8 rounded-xl shadow-xl shadow-slate-400/10 transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 bg-[#354f52]/10 text-[#2f3e46] rounded-2xl flex items-center justify-center mb-5 group-hover:bg-[#354f52] group-hover:text-white transition-all">
              <ClipboardList className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-[#2f3e46] mb-2">Safety Admin</h2>
            <p className="text-slate-500 text-sm leading-relaxed">
              Access the sorted SIF precursor triage queue, AI reasoning inspections, and site risk analytics.
            </p>
          </div>
          <div className="mt-8 flex items-center gap-2 text-[#2f3e46] text-sm font-bold group-hover:translate-x-1 transition-transform">
            <span>Open Admin Hub</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

      </div>

      {/* Footer */}
      <div className="mt-16 text-slate-500 text-xs tracking-wide">
        SIH 2026 • Minimalist Safety Intelligence Platform
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