import  { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mic, ArrowRight, ShieldCheck, Sparkles, CheckCircle2, RotateCcw } from 'lucide-react';
import { api } from '../api';

export default function WorkerAnalyzer() {
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('en');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [isListening, setIsListening] = useState(false);

  // Quick fill preset chips for fast hackathon demoing
  const presets = [
    "Rail missing on storage tank roof, worker almost fell.",
    "Safety lockout tag missing on main reactor isolation valves.",
    "Hydraulic crane boom tipped over during pipe lifting."
  ];

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    try {
      const data = await api.analyzeReport(text);
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Error connecting to backend analysis engine.");
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceMock = () => {
    setIsListening(true);
    setTimeout(() => {
      setText("Contractor was working near the high pressure valve without proper isolation tag.");
      setIsListening(false);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-[#dce4e1] text-[#2c3e37] flex flex-col items-center justify-start p-4 md:p-8">
      {/* Top Navigation Bar */}
      <div className="w-full max-w-xl flex justify-between items-center mb-8">
        <Link to="/" className="text-sm font-semibold tracking-wide uppercase opacity-70 hover:opacity-100 transition-opacity">
          ← Back Home
        </Link>
        <div className="flex items-center gap-2 bg-white/60 backdrop-blur-md px-3 py-1.5 rounded-full text-xs font-medium shadow-sm">
          <span>🌐 Language:</span>
          <select 
            value={language} 
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-transparent outline-none font-semibold cursor-pointer"
          >
            <option value="en">English</option>
            <option value="hi">Hindi (हिंदी)</option>
            <option value="as">Assamese (অসমীয়া)</option>
          </select>
        </div>
      </div>

      {/* Main Container */}
      <div className="w-full max-w-xl bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-6 md:p-10 shadow-xl shadow-slate-400/10 border border-white/50">
        
        {/* Header Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-[#52796f]/10 text-[#354f52] mb-3">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[#2f3e46]">
            Field Incident Report
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Keep our sites safe. Record unsafe acts, conditions, or near-misses.
          </p>
        </div>

        {!result ? (
          /* Input Form */
          <form onSubmit={handleAnalyze} className="space-y-6">
            
            {/* Quick Fill Chips */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Quick Preset Scenarios
              </label>
              <div className="flex flex-wrap gap-2">
                {presets.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setText(preset)}
                    className="text-xs bg-[#f0f4f3] hover:bg-[#e2ece9] text-[#354f52] px-3 py-1.5 rounded-xl transition-colors border border-[#cad2c5]/50 text-left"
                  >
                    ✨ {preset.slice(0, 32)}...
                  </button>
                ))}
              </div>
            </div>

            {/* Text Area with Voice Button */}
            <div className="relative">
              <textarea
                rows="4"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Describe what happened or what control was missing..."
                className="w-full bg-[#f8faf9] border border-slate-200 rounded-2xl p-4 text-sm md:text-base text-slate-700 outline-none focus:border-[#52796f] focus:ring-2 focus:ring-[#52796f]/20 transition-all resize-none shadow-inner"
              />
              
              <div className="absolute right-3 bottom-3 flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleVoiceMock}
                  className={`p-2.5 rounded-xl flex items-center gap-1.5 text-xs font-medium transition-all ${
                    isListening 
                      ? 'bg-rose-500 text-white animate-pulse' 
                      : 'bg-[#52796f]/10 text-[#354f52] hover:bg-[#52796f]/20'
                  }`}
                  title="Simulate Voice Input"
                >
                  <Mic className="w-4 h-4" />
                  {isListening ? "Listening..." : "Voice"}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="w-full bg-[#354f52] hover:bg-[#2f3e46] text-white py-4 rounded-2xl font-semibold shadow-lg shadow-[#354f52]/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span>
              ) : (
                <>
                  <span>Analyze & Submit Report</span>
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Success & Safety Tips State (Minimalist Confirmation) */
          <div className="space-y-6 text-center animate-fadeIn">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mb-2">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            
            <h2 className="text-xl font-bold text-slate-800">Report Successfully Logged</h2>
            <p className="text-sm text-slate-600 px-4">
              Thank you for keeping our field operations safe. Your report has been securely recorded.
            </p>

            {/* Dynamic Tips / Recommended Check Box */}
            {result.result.is_sif_precursor && result.result.recommended_check ? (
              <div className="bg-[#f0f4f3] border border-[#cad2c5] p-5 rounded-2xl text-left">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#354f52] mb-1">
                  <Sparkles className="w-4 h-4" /> Safety Team Action Triggered
                </div>
                <p className="text-xs md:text-sm text-slate-700 font-medium">
                  {result.result.recommended_check}
                </p>
              </div>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-2xl text-emerald-800 text-xs font-medium">
                Standard routine entry. No immediate work stoppage required.
              </div>
            )}

            <button
              onClick={() => { setResult(null); setText(''); }}
              className="inline-flex items-center gap-2 text-sm font-semibold text-[#354f52] hover:underline pt-4"
            >
              <RotateCcw className="w-4 h-4" /> Submit Another Report
            </button>
          </div>
        )}

      </div>
    </div>
  );
}