import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Mic, Square, ArrowRight, ShieldCheck, Sparkles, CheckCircle2, RotateCcw, Loader2, Sun, Moon } from 'lucide-react';
import { api } from '../api';
import { useVoiceRecorder } from '../useVoiceRecorder';

// The device clock decides the default shift. Night shift is 18:00 to 06:00.
//
// Site, activity and shift were all hardcoded here - every live submission was filed as
// "Rig 4", "General Operations", "day". That is not a cosmetic default: the dashboard
// ranks sites by precursor DENSITY, so one site absorbed every real report and its rate
// climbed while every other site's stayed frozen, and /aggregate/shifts saw a fleet that
// never worked nights.
function defaultShift() {
  const hour = new Date().getHours();
  return hour >= 18 || hour < 6 ? 'night' : 'day';
}

export default function WorkerAnalyzer() {
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('en');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [voiceError, setVoiceError] = useState('');
  const [site, setSite] = useState('');
  const [activity, setActivity] = useState('');
  const [shift, setShift] = useState(defaultShift);
  const [sites, setSites] = useState([]);
  const [activities, setActivities] = useState([]);
  const [metaError, setMetaError] = useState('');

  // The site list is whatever the database already holds, so a report is filed against a
  // site the aggregates recognise instead of a fresh spelling that splits it in two.
  useEffect(() => {
    let cancelled = false;

    api.getMeta()
      .then((meta) => {
        if (cancelled) return;
        setSites(meta.sites ?? []);
        setActivities(meta.activities ?? []);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('Failed to load site list:', err);
        setMetaError('Could not load the site list. Type your site name instead.');
      });

    return () => { cancelled = true; };
  }, []);

  const { isRecording, isTranscribing, startRecording, stopRecording } = useVoiceRecorder({
    language,
    onTranscribed: (transcribedText) => {
      setText((prev) => (prev ? `${prev} ${transcribedText}` : transcribedText));
      setVoiceError('');
    },
    onError: (message) => setVoiceError(message),
  });

 const handleAnalyze = async (e) => {
  e.preventDefault();

  if (!text.trim() || !site.trim() || !activity.trim()) return;

  setLoading(true);

  try {
    const data = await api.submitWorkerReport({
      report_text: text,
      site: site.trim(),
      activity: activity.trim(),
      shift,
      is_contractor: false,
    });

    setResult(data);

  } catch (err) {
    console.error(err);

    alert(
      err.message || "Error submitting safety report."
    );

  } finally {
    setLoading(false);
  }
};

  return (
    <div className="min-h-screen bg-[#dce4e1] text-[#2c3e37] flex flex-col items-center justify-start p-4 md:p-8">
      <div className="w-full max-w-xl flex flex-wrap justify-between items-center gap-3 mb-6 md:mb-8">
        <Link
          to="/"
          className="text-xs sm:text-sm font-semibold tracking-wide uppercase opacity-70 hover:opacity-100 transition-opacity"
        >
          ← Back Home
        </Link>

        <div className="flex items-center gap-2 bg-white/80 px-3 sm:px-4 py-2 rounded-full text-sm font-medium shadow-sm">
          <span>🌐</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-transparent outline-none font-semibold cursor-pointer text-base"
          >
            <option value="en">English</option>
            <option value="hi">हिंदी (Hindi)</option>
            <option value="or">ଓଡ଼ିଆ (Odia)</option>
          </select>
        </div>
      </div>

      <div className="w-full max-w-xl bg-white/90 rounded-[2rem] p-5 sm:p-6 md:p-10 shadow-xl border border-white/50">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#52796f]/10 text-[#354f52] mb-3">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[#2f3e46]">
            Report a Safety Concern
          </h1>
          <p className="text-base text-slate-500 mt-2">
            Speak or type. It's okay to keep it simple.
          </p>
        </div>

        {!result ? (
          <form onSubmit={handleAnalyze} className="space-y-6">
            <div className="flex flex-col items-center gap-3">
              <button
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isTranscribing}
                className={`flex flex-col items-center justify-center w-24 h-24 sm:w-28 sm:h-28 rounded-full shadow-lg transition-all ${
                  isRecording ? 'bg-rose-500 animate-pulse' : 'bg-[#52796f] hover:bg-[#3f5f57]'
                } disabled:opacity-60`}
              >
                {isTranscribing ? (
                  <Loader2 className="w-9 h-9 text-white animate-spin" />
                ) : isRecording ? (
                  <Square className="w-9 h-9 text-white" />
                ) : (
                  <Mic className="w-9 h-9 text-white" />
                )}
              </button>

              <p className="text-base font-semibold text-[#354f52]">
                {isTranscribing
                  ? 'Listening carefully...'
                  : isRecording
                  ? 'Recording — tap to stop'
                  : 'Tap to speak your report'}
              </p>

              {voiceError && (
                <p className="text-sm text-rose-600 text-center max-w-xs">{voiceError}</p>
              )}
            </div>

            <div className="flex items-center gap-3 text-slate-400 text-sm">
              <div className="flex-1 h-px bg-slate-200" />
              or type instead
              <div className="flex-1 h-px bg-slate-200" />
            </div>

            <textarea
              rows="4"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="What happened? What was missing?"
              className="w-full bg-[#f8faf9] border border-slate-200 rounded-2xl p-4 text-base text-slate-700 outline-none focus:border-[#52796f] focus:ring-2 focus:ring-[#52796f]/20 transition-all resize-none"
            />

            <div className="space-y-4">
              <div>
                <label htmlFor="site" className="block text-sm font-semibold text-[#354f52] mb-2">
                  Where are you?
                </label>

                {sites.length > 0 ? (
                  <select
                    id="site"
                    value={site}
                    onChange={(e) => setSite(e.target.value)}
                    className="w-full bg-[#f8faf9] border border-slate-200 rounded-2xl p-4 text-base text-slate-700 outline-none focus:border-[#52796f] focus:ring-2 focus:ring-[#52796f]/20 transition-all cursor-pointer"
                  >
                    <option value="">Select your site</option>
                    {sites.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                ) : (
                  // Only when the site list could not be fetched. A worker standing in front
                  // of a hazard must still be able to file, so fall back to typing it.
                  <input
                    id="site"
                    type="text"
                    value={site}
                    onChange={(e) => setSite(e.target.value)}
                    placeholder="Site name"
                    className="w-full bg-[#f8faf9] border border-slate-200 rounded-2xl p-4 text-base text-slate-700 outline-none focus:border-[#52796f] focus:ring-2 focus:ring-[#52796f]/20 transition-all"
                  />
                )}

                {metaError && (
                  <p className="text-sm text-amber-700 mt-2">{metaError}</p>
                )}
              </div>

              <div>
                <label htmlFor="activity" className="block text-sm font-semibold text-[#354f52] mb-2">
                  What were you doing?
                </label>
                <input
                  id="activity"
                  type="text"
                  list="activity-options"
                  value={activity}
                  onChange={(e) => setActivity(e.target.value)}
                  placeholder="e.g. Lifting, Confined space entry"
                  className="w-full bg-[#f8faf9] border border-slate-200 rounded-2xl p-4 text-base text-slate-700 outline-none focus:border-[#52796f] focus:ring-2 focus:ring-[#52796f]/20 transition-all"
                />
                <datalist id="activity-options">
                  {activities.map((a) => (
                    <option key={a} value={a} />
                  ))}
                </datalist>
              </div>

              <div>
                <span className="block text-sm font-semibold text-[#354f52] mb-2">Shift</span>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'day', label: 'Day', icon: Sun },
                    { value: 'night', label: 'Night', icon: Moon },
                  ].map(({ value, label, icon: Icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setShift(value)}
                      className={`flex items-center justify-center gap-2 py-4 rounded-2xl text-base font-semibold border transition-all ${
                        shift === value
                          ? 'bg-[#354f52] text-white border-[#354f52] shadow-sm'
                          : 'bg-[#f8faf9] text-slate-600 border-slate-200 hover:border-[#52796f]'
                      }`}
                    >
                      <Icon className="w-5 h-5" /> {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !text.trim() || !site.trim() || !activity.trim()}
              className="w-full bg-[#354f52] hover:bg-[#2f3e46] text-white py-5 rounded-2xl font-semibold text-lg shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-spin rounded-full h-6 w-6 border-b-2 border-white" />
              ) : (
                <>
                  <span>Submit Report</span>
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>
        ) : (
          <div className="space-y-6 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mb-2">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <h2 className="text-xl font-bold text-slate-800">Thank you. Report received.</h2>
            <p className="text-base text-slate-600 px-4">
              Your report helps keep everyone on site safe.
            </p>

            {result.result.is_sif_precursor && result.result.recommended_check ? (
              <div className="bg-[#f0f4f3] border border-[#cad2c5] p-5 rounded-2xl text-left">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-[#354f52] mb-2">
                  <Sparkles className="w-4 h-4" /> A safety officer has been notified
                </div>
                <p className="text-base text-slate-700 font-medium">
                  {result.result.recommended_check}
                </p>
              </div>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-2xl text-emerald-800 text-base font-medium">
                Logged. No immediate action needed.
              </div>
            )}

            <button
              onClick={() => {
                setResult(null);
                setText('');
              }}
              className="inline-flex items-center gap-2 text-base font-semibold text-[#354f52] hover:underline pt-4"
            >
              <RotateCcw className="w-4 h-4" /> Submit Another Report
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
















