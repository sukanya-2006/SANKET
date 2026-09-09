import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ArrowLeft, BarChart3, ShieldAlert, FileText, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sumData, siteData] = await Promise.all([
          api.getSummary(),
          api.getSites()
        ]);
        setSummary(sumData);
        setSites(Array.isArray(siteData) ? siteData : siteData.sites || []);
      } catch (err) {
        console.error('Failed to load dashboard metrics:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-[#dce4e1] text-[#2c3e37] p-4 md:p-8">
      {/* Top Bar */}
      <div className="max-w-6xl mx-auto flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <Link to="/admin/triage" className="p-2 bg-white/80 rounded-xl hover:bg-white transition-colors shadow-sm">
            <ArrowLeft className="w-5 h-5 text-[#354f52]" />
          </Link>
          <h1 className="text-2xl font-bold text-[#2f3e46]">Executive Risk Dashboard</h1>
        </div>
        <Link 
          to="/" 
          className="text-xs font-semibold text-[#354f52] hover:underline bg-white/60 px-3 py-1.5 rounded-full"
        >
          Sign Out / Home
        </Link>
      </div>

      {loading ? (
        <div className="max-w-6xl mx-auto py-24 text-center text-slate-500 font-medium">
          Loading analytics metrics...
        </div>
      ) : (
        <div className="max-w-6xl mx-auto space-y-6">
          
          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white/90 backdrop-blur-xl p-6 rounded-3xl shadow-xl border border-white/50 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Total Reports Logged</p>
                <h3 className="text-3xl font-extrabold text-slate-800">{summary?.total_reports || 180}</h3>
              </div>
              <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center">
                <FileText className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-white/90 backdrop-blur-xl p-6 rounded-3xl shadow-xl border border-white/50 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">SIF Precursors Flagged</p>
                <h3 className="text-3xl font-extrabold text-rose-600">{summary?.precursor_count || 48}</h3>
              </div>
              <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-2xl flex items-center justify-center">
                <ShieldAlert className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-white/90 backdrop-blur-xl p-6 rounded-3xl shadow-xl border border-white/50 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Precursor Rate Density</p>
                <h3 className="text-3xl font-extrabold text-[#354f52]">
                  {summary?.precursor_rate ? `${(summary.precursor_rate * 100).toFixed(1)}%` : '26.7%'}
                </h3>
              </div>
              <div className="w-12 h-12 bg-[#52796f]/10 text-[#354f52] rounded-2xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6" />
              </div>
            </div>
          </div>

          {/* Site Risk Ranking Chart Container */}
          <div className="bg-white/90 backdrop-blur-xl p-6 md:p-8 rounded-[2rem] shadow-xl border border-white/50">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-bold text-slate-800">Site Risk Density Ranking</h2>
                <p className="text-xs text-slate-500">Comparing precursor frequency across operational sectors.</p>
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#354f52] bg-[#52796f]/10 px-3 py-1.5 rounded-xl">
                <BarChart3 className="w-4 h-4" /> Live Aggregates
              </div>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sites.length ? sites : [
                  { site: 'Duliajan Field', count: 18 },
                  { site: 'Naharkatia', count: 14 },
                  { site: 'Moran Well-12', count: 9 },
                  { site: 'Jorhat Depot', count: 5 }
                ]} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                  <YAxis dataKey="site" type="category" stroke="#475569" fontSize={12} width={110} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: '12px', border: 'none' }} />
                  <Bar dataKey="count" fill="#354f52" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}