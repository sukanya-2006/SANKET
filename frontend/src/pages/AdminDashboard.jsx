import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ArrowLeft, BarChart3, ShieldAlert, FileText, TrendingUp, AlertTriangle, Database } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

// There is deliberately no placeholder data anywhere in this file.
//
// Every metric below used to fall back to an invented number - `summary?.total_reports || 180`,
// `|| 48`, a hardcoded '26.7%', and four made-up Assam sites in the chart - displayed under a
// badge reading "Live Aggregates". Two things were wrong with that.
//
// First, it was not a fallback that rarely fired. getSites() returns
// { ranked, insufficient_volume, min_group_n }, and this file read `siteData.sites`, which does
// not exist, so the chart fell through to the invented rows every single time. That panel had
// never once shown a real number.
//
// Second, `||` on a number treats 0 as missing. A genuine "0 precursors found" rendered as 48.
// The one result a safety dashboard must be able to state plainly is the one it could not show.
//
// Showing confidently wrong metrics to someone non-technical is a worse failure than showing
// nothing. So: loading says loading, an error says what broke, and no data says no data.

function formatRate(rate) {
  if (typeof rate !== 'number' || Number.isNaN(rate)) return null;
  return `${(rate * 100).toFixed(1)}%`;
}

function Kpi({ label, value, accent, icon: Icon, iconWrap }) {
  const missing = value === null || value === undefined;
  return (
    <div className="bg-white/90 backdrop-blur-xl p-6 rounded-3xl shadow-xl border border-white/50 flex items-center justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">{label}</p>
        <h3 className={`text-3xl font-extrabold ${missing ? 'text-slate-300' : accent}`}>
          {missing ? '—' : value}
        </h3>
      </div>
      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${iconWrap}`}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [ranked, setRanked] = useState([]);
  const [thinGroups, setThinGroups] = useState([]);
  const [minGroupN, setMinGroupN] = useState(0);
  const [dataSource, setDataSource] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const [sumData, siteData, health] = await Promise.all([
          api.getSummary(),
          api.getSites(),
          // Never let a failed health check hide the metrics - it only drives a badge.
          api.getHealth().catch(() => null)
        ]);
        if (cancelled) return;
        setSummary(sumData);
        setRanked(siteData.ranked);
        setThinGroups(siteData.insufficientVolume);
        setMinGroupN(siteData.minGroupN);
        setDataSource(health?.data_source ?? null);
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load dashboard metrics:', err);
        setError(err.message || 'Could not reach the API.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadData();
    return () => { cancelled = true; };
  }, []);

  const isStub = dataSource === 'seeded_stub';
  const chartRows = ranked.map((s) => ({
    site: s.site,
    precursors: s.precursor_count,
    reports: s.report_count,
    rate: s.precursor_rate,
    topRule: s.top_rule
  }));

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

      {/* Demo-data badge. If the API is serving the seeded stub, say so up front rather than
          letting someone read fixture numbers off the screen as though they were live. */}
      {isStub && (
        <div className="max-w-6xl mx-auto mb-6 flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-2xl">
          <Database className="w-5 h-5 shrink-0" />
          <p className="text-sm">
            <span className="font-semibold">Demo data.</span>{' '}
            The API has no database configured, so these numbers come from the seeded sample set,
            not from live reports.
          </p>
        </div>
      )}

      {loading ? (
        <div className="max-w-6xl mx-auto py-24 text-center text-slate-500 font-medium">
          Loading analytics metrics...
        </div>
      ) : error ? (
        <div className="max-w-6xl mx-auto bg-white/90 border border-rose-200 rounded-3xl shadow-xl p-8 flex items-start gap-4">
          <AlertTriangle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <h2 className="font-bold text-slate-800 mb-1">Could not load the dashboard</h2>
            <p className="text-sm text-slate-600 mb-3">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="text-xs font-semibold text-[#354f52] bg-[#52796f]/10 px-3 py-1.5 rounded-xl hover:bg-[#52796f]/20 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      ) : (
        <div className="max-w-6xl mx-auto space-y-6">

          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Kpi
              label="Total Reports Logged"
              value={summary?.total_reports ?? null}
              accent="text-slate-800"
              icon={FileText}
              iconWrap="bg-blue-50 text-blue-600"
            />
            <Kpi
              label="SIF Precursors Flagged"
              value={summary?.precursor_count ?? null}
              accent="text-rose-600"
              icon={ShieldAlert}
              iconWrap="bg-rose-50 text-rose-600"
            />
            <Kpi
              label="Precursor Rate Density"
              value={formatRate(summary?.precursor_rate)}
              accent="text-[#354f52]"
              icon={TrendingUp}
              iconWrap="bg-[#52796f]/10 text-[#354f52]"
            />
          </div>

          {/* Site Risk Ranking Chart Container */}
          <div className="bg-white/90 backdrop-blur-xl p-6 md:p-8 rounded-[2rem] shadow-xl border border-white/50">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-bold text-slate-800">Site Risk Density Ranking</h2>
                <p className="text-xs text-slate-500">
                  Precursors per site, ranked by rate so a site is not punished for reporting diligently.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#354f52] bg-[#52796f]/10 px-3 py-1.5 rounded-xl">
                <BarChart3 className="w-4 h-4" /> {isStub ? 'Sample Data' : 'Live Aggregates'}
              </div>
            </div>

            {chartRows.length === 0 ? (
              <div className="h-72 flex flex-col items-center justify-center text-center text-slate-500">
                <BarChart3 className="w-8 h-8 mb-3 text-slate-300" />
                <p className="font-medium">No site has enough classified reports to rank yet.</p>
                <p className="text-xs mt-1 max-w-md">
                  A site needs at least {minGroupN} classified reports before a rate is shown, so a
                  single report cannot put a site at the top of the board.
                </p>
              </div>
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartRows} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                    <XAxis type="number" stroke="#94a3b8" fontSize={12} allowDecimals={false} />
                    <YAxis dataKey="site" type="category" stroke="#475569" fontSize={12} width={130} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: '12px', border: 'none' }}
                      formatter={(value, name, entry) => {
                        const row = entry?.payload;
                        if (!row) return value;
                        return [
                          `${row.precursors} of ${row.reports} reports (${formatRate(row.rate)})`,
                          row.topRule ? `Most common rule: ${row.topRule.replace(/_/g, ' ')}` : 'No precursors'
                        ];
                      }}
                    />
                    <Bar dataKey="precursors" fill="#354f52" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Groups held back by the small-denominator guard. Shown, not hidden - a site with
                two reports and two precursors is not the riskiest site in the company, and
                silently dropping it would leave someone wondering where it went. */}
            {thinGroups.length > 0 && (
              <div className="mt-6 pt-5 border-t border-slate-200">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Too few reports to rank (under {minGroupN})
                </p>
                <div className="flex flex-wrap gap-2">
                  {thinGroups.map((g) => (
                    <span
                      key={g.site}
                      className="text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-xl"
                    >
                      {g.site} · {g.precursor_count}/{g.report_count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
