import { useState } from 'react';
import ChatInterface from '../components/ChatInterface';
import { tools, type ChatMessage } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { BookOpen, Beaker, Globe, Calculator, Palette, AlertTriangle, X, Loader2, CheckCircle, Shield } from 'lucide-react';

const subjects = [
  { id: 'mathematics', label: 'Mathematics', icon: Calculator, color: 'bg-sky/30' },
  { id: 'language', label: 'Language', icon: BookOpen, color: 'bg-leaf/15' },
  { id: 'science', label: 'Science', icon: Beaker, color: 'bg-clay/30' },
  { id: 'geography', label: 'Geography', icon: Globe, color: 'bg-sand' },
  { id: 'art', label: 'Creative Arts', icon: Palette, color: 'bg-soft-rose/40' },
];

export default function StudentLearning() {
  const { user } = useAuth();
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [showSafety, setShowSafety] = useState(false);
  const [safetyText, setSafetyText] = useState('');
  const [safetySending, setSafetySending] = useState(false);
  const [safetySent, setSafetySent] = useState(false);
  const displayName = user && 'name' in user ? user.name : 'Explorer';
  const selected = subjects.find(s => s.id === selectedSubject);

  const handleSafetyReport = async () => {
    if (!safetyText.trim()) return;
    setSafetySending(true);
    try {
      await tools.chat({
        message: `[SAFETY REPORT] ${safetyText}`,
        interface_type: 'safety_report',
      });
      setSafetySent(true);
      setTimeout(() => {
        setShowSafety(false);
        setSafetyText('');
        setSafetySent(false);
      }, 2000);
    } catch {
      setSafetySent(true);
    } finally {
      setSafetySending(false);
    }
  };

  if (selected) {
    return (
      <div className="animate-fade-in">
        <div className="flex items-center gap-3 mb-2">
          <button onClick={() => setSelectedSubject(null)} className="text-sm text-eco-accent hover:text-eco-hover transition-colors">
            ← Subjects
          </button>
          <button onClick={() => setShowSafety(true)} className="ml-auto p-2 rounded-xl text-warning hover:bg-warning/10 transition-colors" title="Report a concern">
            <AlertTriangle size={16} />
          </button>
        </div>

        <div className="mb-3 p-3 bg-sky/10 border border-sky/20 rounded-xl flex items-start gap-2">
          <Shield size={14} className="text-ink mt-0.5 shrink-0" />
          <p className="text-xs text-eco-text/60">
            Your conversations are private but monitored for safety. A trusted adult can see if something concerning comes up. You can always report a concern using the warning icon above.
          </p>
        </div>

        {showSafety && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
            <div className="bg-eco-card rounded-2xl border border-eco-border p-6 w-full max-w-sm mx-4 shadow-xl animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-serif text-ink">Report a Concern</h3>
                <button onClick={() => { setShowSafety(false); setSafetyText(''); setSafetySent(false); }} className="p-1 rounded-lg hover:bg-sand/50"><X size={18} /></button>
              </div>
              {safetySent ? (
                <div className="text-center py-6">
                  <CheckCircle className="mx-auto text-leaf mb-3" size={36} />
                  <p className="text-sm text-ink font-medium">Your report has been sent.</p>
                  <p className="text-xs text-eco-text/60 mt-1">A trusted adult will review this.</p>
                </div>
              ) : (
                <>
                  <p className="text-sm text-eco-text/60 mb-4">If something made you uncomfortable, please tell a trusted adult. You can also let us know here.</p>
                  <textarea
                    rows={3}
                    value={safetyText}
                    onChange={e => setSafetyText(e.target.value)}
                    placeholder="What happened?"
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf resize-none mb-3"
                  />
                  <button
                    onClick={handleSafetyReport}
                    disabled={safetySending || !safetyText.trim()}
                    className="w-full py-2 bg-warning hover:bg-warning/80 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {safetySending && <Loader2 size={14} className="animate-spin" />}
                    Send report
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        <ChatInterface
          title={selected.label}
          subtitle="Ask me anything — I'm here to help you learn!"
          placeholder={`What would you like to explore in ${selected.label.toLowerCase()}?`}
          welcomeMessage={`Hi ${displayName}! Ready to explore ${selected.label}? Ask me anything and we'll learn together. Remember, there are no wrong questions!`}
          onSend={async (message: string, history: ChatMessage[]) => {
            const res = await tools.studentTutor({ message, subject: selected.id, history });
            return res.response;
          }}
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="text-center mb-6">
        <h2 className="text-3xl font-serif text-ink">Hello, {displayName}!</h2>
        <p className="text-eco-text/60 mt-2">What would you like to learn about today?</p>
      </div>

      <div className="max-w-2xl mx-auto mb-4 p-3 bg-sky/10 border border-sky/20 rounded-xl flex items-start gap-2">
        <Shield size={14} className="text-ink mt-0.5 shrink-0" />
        <p className="text-xs text-eco-text/60">
          Your learning sessions are private and safe. Your teacher can see your progress to help you learn better.
          If you ever feel uncomfortable, use the warning icon during a session to tell a trusted adult.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-2xl mx-auto">
        {subjects.map(subj => (
          <button
            key={subj.id}
            onClick={() => setSelectedSubject(subj.id)}
            className="group bg-eco-card rounded-2xl border border-eco-border p-6 hover:border-leaf/40 hover:shadow-sm transition-all duration-200 text-center"
          >
            <div className={`w-14 h-14 rounded-2xl ${subj.color} flex items-center justify-center mx-auto mb-3`}>
              <subj.icon size={24} className="text-ink" />
            </div>
            <h3 className="font-sans text-base font-semibold text-ink">{subj.label}</h3>
          </button>
        ))}
      </div>
    </div>
  );
}
