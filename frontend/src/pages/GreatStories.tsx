import { useState, useEffect } from 'react';
import { tools } from '../lib/api';
import { Loader2, BookMarked, Plus, Trash2, ChevronRight } from 'lucide-react';

export default function GreatStories() {
  const [view, setView] = useState<'create' | 'library'>('create');
  const [topic, setTopic] = useState('');
  const [ageGroup, setAgeGroup] = useState('6-9');
  const [storyType, setStoryType] = useState('');
  const [additional, setAdditional] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stories, setStories] = useState<any[]>([]);
  const [loadingStories, setLoadingStories] = useState(false);

  const loadStories = async () => {
    setLoadingStories(true);
    try {
      const res = await tools.listGreatStories();
      setStories(res.stories || []);
    } catch {} finally { setLoadingStories(false); }
  };

  useEffect(() => {
    if (view === 'library') loadStories();
  }, [view]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult('');
    try {
      const res = await tools.greatStory({ topic, age_group: ageGroup, story_type: storyType, additional_context: additional });
      setResult(res.content);
    } catch (e: any) {
      setError(e.message || 'Failed to generate story');
    } finally { setLoading(false); }
  };

  const handleDelete = async (id: string) => {
    try {
      await tools.deleteGreatStory(id);
      setStories(s => s.filter(st => st.id !== id));
    } catch {}
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-serif text-ink">Great Stories</h2>
          <p className="text-sm text-eco-text/60 mt-1">Create and explore Montessori Great Stories</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setView('create')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${view === 'create' ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'}`}>
            <Plus size={14} className="inline mr-1" /> Create
          </button>
          <button onClick={() => setView('library')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${view === 'library' ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'}`}>
            <BookMarked size={14} className="inline mr-1" /> Library
          </button>
        </div>
      </div>

      {view === 'create' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Story topic</label>
                <input value={topic} onChange={e => setTopic(e.target.value)} required
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                  placeholder="e.g., The Coming of Life, The Story of Numbers" />
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
                  <label className="block text-sm font-medium text-ink mb-1.5">Story type</label>
                  <select value={storyType} onChange={e => setStoryType(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf">
                    <option value="">Classic Great Story</option>
                    <option value="cosmic">Cosmic Education</option>
                    <option value="cultural">Cultural</option>
                    <option value="custom">Custom theme</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Additional context</label>
                <textarea value={additional} onChange={e => setAdditional(e.target.value)} rows={3}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf resize-none"
                  placeholder="Specific elements to include, connections to make..." />
              </div>
              <button type="submit" disabled={loading}
                className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                {loading ? <><Loader2 size={16} className="animate-spin" /> Creating story...</> : 'Generate Great Story'}
              </button>
            </form>
          </div>
          <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
            <h3 className="font-sans text-sm font-semibold text-ink mb-3">Generated Story</h3>
            {error && <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3">{error}</div>}
            {result ? (
              <div className="prose text-sm text-eco-text leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto">{result}</div>
            ) : (
              <p className="text-sm text-eco-text/40 italic">Your story will appear here...</p>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          {loadingStories ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-leaf" size={24} /></div>
          ) : stories.length === 0 ? (
            <p className="text-center text-sm text-eco-text/50 py-8">No saved stories yet. Create your first Great Story!</p>
          ) : (
            <div className="space-y-3">
              {stories.map((story: any) => (
                <div key={story.id} className="flex items-center gap-3 p-4 bg-sand/20 rounded-xl">
                  <BookMarked size={18} className="text-clay shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-sans text-sm font-medium text-ink truncate">{story.title || story.topic || 'Untitled'}</h4>
                    <p className="text-xs text-eco-text/50">{story.age_group || ''}</p>
                  </div>
                  <button onClick={() => handleDelete(story.id)} className="p-1.5 rounded-lg text-eco-text/40 hover:text-danger hover:bg-soft-rose/30 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
