import { useState } from 'react';
import { tools } from '../lib/api';
import { Loader2, BookOpen, Target, Layers } from 'lucide-react';

type Mode = 'generate' | 'align' | 'differentiate';

const modes: { key: Mode; icon: typeof BookOpen; label: string; desc: string }[] = [
  { key: 'generate', icon: BookOpen, label: 'Generate Plan', desc: 'Create a full lesson plan' },
  { key: 'align', icon: Target, label: 'Align Curriculum', desc: 'Analyze curriculum alignment' },
  { key: 'differentiate', icon: Layers, label: 'Differentiate', desc: 'Adapt for diverse learners' },
];

export default function LessonPlanning() {
  const [mode, setMode] = useState<Mode>('generate');
  const [topic, setTopic] = useState('');
  const [ageGroup, setAgeGroup] = useState('6-9');
  const [subject, setSubject] = useState('');
  const [duration, setDuration] = useState('45');
  const [additional, setAdditional] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult('');
    try {
      const payload = { topic, age_group: ageGroup, subject, duration, additional_context: additional };
      let res;
      if (mode === 'generate') res = await tools.lessonPlan(payload);
      else if (mode === 'align') res = await tools.align(payload);
      else res = await tools.differentiate(payload);
      setResult(res.content);
    } catch (e: any) {
      setError(e.message || 'Failed to generate. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <h2 className="text-2xl font-serif text-ink mb-1">Lesson Planning</h2>
      <p className="text-sm text-eco-text/60 mb-6">AI-powered tools for Montessori lesson preparation</p>

      <div className="flex gap-2 mb-6">
        {modes.map(m => (
          <button
            key={m.key}
            onClick={() => { setMode(m.key); setResult(''); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              mode === m.key ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'
            }`}
          >
            <m.icon size={16} />
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Topic</label>
              <input value={topic} onChange={e => setTopic(e.target.value)} required
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                placeholder="e.g., Fractions with bead chains" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Age group</label>
                <select value={ageGroup} onChange={e => setAgeGroup(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf">
                  <option value="3-6">3-6 (Primary)</option>
                  <option value="6-9">6-9 (Lower Elementary)</option>
                  <option value="9-12">9-12 (Upper Elementary)</option>
                  <option value="12-15">12-15 (Adolescent)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Duration (min)</label>
                <input type="number" value={duration} onChange={e => setDuration(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Subject area</label>
              <input value={subject} onChange={e => setSubject(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                placeholder="e.g., Mathematics, Language, Science" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Additional context</label>
              <textarea value={additional} onChange={e => setAdditional(e.target.value)} rows={3}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf resize-none"
                placeholder="Any specific requirements, materials, or student needs..." />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading ? <><Loader2 size={16} className="animate-spin" /> Generating...</> : `${modes.find(m => m.key === mode)?.label}`}
            </button>
          </form>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          <h3 className="font-sans text-sm font-semibold text-ink mb-3">Result</h3>
          {error && <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3">{error}</div>}
          {result ? (
            <div className="prose text-sm text-eco-text leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto">{result}</div>
          ) : (
            <p className="text-sm text-eco-text/40 italic">Your generated content will appear here...</p>
          )}
        </div>
      </div>
    </div>
  );
}
