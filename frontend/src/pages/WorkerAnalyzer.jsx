import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mic, Square, ArrowRight, ShieldCheck, Sparkles, CheckCircle2, RotateCcw, Loader2 } from 'lucide-react';
import { api } from '../api';
import { useVoiceRecorder } from '../useVoiceRecorder';

export default function WorkerAnalyzer() {
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('en');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [voiceError, setVoiceError] = useState('');

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
    if (!text.trim()) return;
    setLoading(true);
    try {
      const data = await api.analyzeReport(text);
      setResult(data);
    } catch (err) {
      console.error(err);
      alert('Error connecting to backend analysis engine.');
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

            <button
              type="submit"
              disabled={loading || !text.trim()}
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