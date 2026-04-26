import { useState, useEffect } from 'react';
import { tools } from '../lib/api';
import type { GreatStory } from '../lib/types';
import { Loader2, BookMarked, Plus, Trash2, ArrowLeft, Eye, Copy, Check, Printer, Pencil } from 'lucide-react';
import EditableGeneratedContent, { htmlToPlainText } from '../components/EditableGeneratedContent';

export default function GreatStories() {
  const [view, setView] = useState<'create' | 'library' | 'detail'>('create');
  const [topic, setTopic] = useState('');
  const [ageGroup, setAgeGroup] = useState('6-9');
  const [storyType, setStoryType] = useState('');
  const [additional, setAdditional] = useState('');
  const [result, setResult] = useState('');
  const [createEditedHtml, setCreateEditedHtml] = useState<string | null>(null);
  const [createIsEditing, setCreateIsEditing] = useState(false);
  const [detailEditedHtml, setDetailEditedHtml] = useState<string | null>(null);
  const [detailIsEditing, setDetailIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stories, setStories] = useState<GreatStory[]>([]);
  const [loadingStories, setLoadingStories] = useState(false);
  const [selectedStory, setSelectedStory] = useState<GreatStory | null>(null);
  const [loadingStory, setLoadingStory] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyText = async (text: string, key: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch { /* noop */ }
      document.body.removeChild(ta);
    }
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(prev => (prev === key ? null : prev)), 1800);
  };

  const copyEditableText = (markdown: string, edited: string | null, key: string) => {
    const text = edited !== null ? htmlToPlainText(edited) : markdown;
    return copyText(text, key);
  };

  const loadStories = async () => {
    setLoadingStories(true);
    try {
      const res = await tools.listGreatStories();
      setStories(res.stories);
    } catch {
      // failed to load
    } finally {
      setLoadingStories(false);
    }
  };

  useEffect(() => {
    if (view === 'library') loadStories();
  }, [view]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult('');
    setCreateEditedHtml(null);
    setCreateIsEditing(false);
    try {
      const theme = additional.trim()
        ? `${topic.trim()}\n\nAdditional context: ${additional.trim()}`
        : topic.trim();
      const res = await tools.greatStory({
        theme,
        age_group: ageGroup,
        ...(storyType ? { format_style: storyType } : {}),
      });
      setResult(res.content);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate story');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this story?')) return;
    try {
      await tools.deleteGreatStory(id);
      setStories(s => s.filter(st => st.id !== id));
      if (selectedStory?.id === id) {
        setSelectedStory(null);
        setView('library');
      }
    } catch {
      // failed to delete
    }
  };

  const viewStory = async (story: GreatStory) => {
    setLoadingStory(true);
    setView('detail');
    setDetailEditedHtml(null);
    setDetailIsEditing(false);
    try {
      const full = await tools.getGreatStory(story.id);
      setSelectedStory(full);
    } catch {
      setSelectedStory(story);
    } finally {
      setLoadingStory(false);
    }
  };

  if (view === 'detail' && selectedStory) {
    return (
      <div className="animate-fade-in">
        <button onClick={() => { setView('library'); setSelectedStory(null); }}
          className="mb-4 inline-flex items-center gap-1 text-sm text-eco-accent hover:text-eco-hover transition-colors">
          <ArrowLeft size={14} /> Back to library
        </button>
        <div className={`bg-eco-card rounded-2xl border border-eco-border p-6 ${selectedStory.content ? 'printable-area' : ''}`}>
          {loadingStory ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-leaf" size={24} /></div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4 no-print">
                <h2 className="text-2xl font-serif text-ink">{selectedStory.title || selectedStory.topic || 'Untitled Story'}</h2>
                <div className="flex items-center gap-1.5">
                  <button type="button" onClick={() => setDetailIsEditing(v => !v)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      detailIsEditing
                        ? 'bg-leaf/15 text-leaf-dark hover:bg-leaf/25'
                        : 'text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand'
                    }`}
                    title={detailIsEditing ? 'Switch to view mode' : 'Edit content'}>
                    {detailIsEditing ? <><Eye size={13} /> View</> : <><Pencil size={13} /> Edit</>}
                  </button>
                  <button type="button" onClick={() => copyEditableText(selectedStory.content || '', detailEditedHtml, `detail-${selectedStory.id}`)}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                    title="Copy to clipboard">
                    {copiedKey === `detail-${selectedStory.id}` ? <><Check size={13} className="text-leaf-dark" /> Copied</> : <><Copy size={13} /> Copy</>}
                  </button>
                  <button type="button" onClick={() => window.print()}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                    title="Print or save as PDF">
                    <Printer size={13} /> Print
                  </button>
                  <button onClick={() => handleDelete(selectedStory.id)}
                    className="p-2 rounded-xl text-eco-text/40 hover:text-danger hover:bg-soft-rose/30 transition-colors" title="Delete story">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="flex gap-2 mb-4 text-xs text-eco-text/50 no-print">
                {selectedStory.age_group && <span className="px-2 py-1 bg-sand/50 rounded-lg">{selectedStory.age_group}</span>}
                {selectedStory.story_type && <span className="px-2 py-1 bg-sky/30 rounded-lg">{selectedStory.story_type}</span>}
                {selectedStory.created_at && <span className="px-2 py-1 bg-eco-bg rounded-lg">{new Date(selectedStory.created_at).toLocaleDateString()}</span>}
              </div>
              <div className="hidden print:block mb-6 pb-3 border-b border-eco-border">
                <h1 className="font-serif text-2xl text-ink m-0">{selectedStory.title || selectedStory.topic || 'Untitled Story'}</h1>
                {selectedStory.age_group && <p className="text-sm text-eco-text/70 mt-1">Ages {selectedStory.age_group}</p>}
              </div>
              <EditableGeneratedContent
                markdown={selectedStory.content || ''}
                editedHtml={detailEditedHtml}
                isEditing={detailIsEditing}
                onEditedHtmlChange={setDetailEditedHtml}
                variant="prose"
              />
            </>
          )}
        </div>
      </div>
    );
  }

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
          <div className={`bg-eco-card rounded-2xl border border-eco-border p-6 ${result ? 'printable-area' : ''}`}>
            <div className="flex items-center justify-between mb-3 no-print">
              <h3 className="font-sans text-sm font-semibold text-ink">Generated Story</h3>
              {result && (
                <div className="flex gap-1.5">
                  <button type="button" onClick={() => setCreateIsEditing(v => !v)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      createIsEditing
                        ? 'bg-leaf/15 text-leaf-dark hover:bg-leaf/25'
                        : 'text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand'
                    }`}
                    title={createIsEditing ? 'Switch to view mode' : 'Edit content'}>
                    {createIsEditing ? <><Eye size={13} /> View</> : <><Pencil size={13} /> Edit</>}
                  </button>
                  <button type="button" onClick={() => copyEditableText(result, createEditedHtml, 'create')}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                    title="Copy to clipboard">
                    {copiedKey === 'create' ? <><Check size={13} className="text-leaf-dark" /> Copied</> : <><Copy size={13} /> Copy</>}
                  </button>
                  <button type="button" onClick={() => window.print()}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                    title="Print or save as PDF">
                    <Printer size={13} /> Print
                  </button>
                </div>
              )}
            </div>
            <div className="hidden print:block mb-6 pb-3 border-b border-eco-border">
              <h1 className="font-serif text-2xl text-ink m-0">{topic || 'Great Story'}</h1>
              {ageGroup && <p className="text-sm text-eco-text/70 mt-1">Ages {ageGroup}</p>}
            </div>
            {error && <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3 no-print">{error}</div>}
            {result ? (
              <div className="max-h-[60vh] overflow-y-auto print:max-h-none print:overflow-visible">
                <EditableGeneratedContent
                  markdown={result}
                  editedHtml={createEditedHtml}
                  isEditing={createIsEditing}
                  onEditedHtmlChange={setCreateEditedHtml}
                  variant="prose"
                />
              </div>
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
              {stories.map(story => (
                <div key={story.id} className="flex items-center gap-3 p-4 bg-sand/20 rounded-xl">
                  <BookMarked size={18} className="text-clay shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-sans text-sm font-medium text-ink truncate">{story.title || story.topic || 'Untitled'}</h4>
                    <p className="text-xs text-eco-text/50">{story.age_group || ''}</p>
                  </div>
                  <button onClick={() => viewStory(story)}
                    className="p-1.5 rounded-lg text-eco-text/40 hover:text-ink hover:bg-sand/50 transition-colors" title="View story">
                    <Eye size={14} />
                  </button>
                  <button onClick={() => handleDelete(story.id)}
                    className="p-1.5 rounded-lg text-eco-text/40 hover:text-danger hover:bg-soft-rose/30 transition-colors" title="Delete story">
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
