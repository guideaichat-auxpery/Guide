import { useState, useEffect } from 'react';
import { notes as notesApi } from '../lib/api';
import type { PlanningNote } from '../lib/types';
import { Loader2, Plus, Trash2, Edit3, Save, X, StickyNote, Bold, Italic, List } from 'lucide-react';

export default function PlanningNotes() {
  const [notesList, setNotesList] = useState<PlanningNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<PlanningNote | null>(null);
  const [creating, setCreating] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formContent, setFormContent] = useState('');
  const [formCategory, setFormCategory] = useState('');
  const [saving, setSaving] = useState(false);
  const [expandedNote, setExpandedNote] = useState<string | null>(null);

  const loadNotes = async () => {
    setLoading(true);
    try {
      const res = await notesApi.list();
      setNotesList(res.notes);
    } catch {
      // failed to load
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadNotes(); }, []);

  const startCreate = () => {
    setCreating(true);
    setEditing(null);
    setFormTitle('');
    setFormContent('');
    setFormCategory('');
  };

  const startEdit = (note: PlanningNote) => {
    setEditing(note);
    setCreating(false);
    setFormTitle(note.title);
    setFormContent(note.content);
    setFormCategory(note.category || '');
  };

  const cancel = () => {
    setCreating(false);
    setEditing(null);
  };

  const insertFormatting = (prefix: string, suffix: string) => {
    const textarea = document.getElementById('note-content') as HTMLTextAreaElement | null;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = formContent.substring(start, end);
    const newContent = formContent.substring(0, start) + prefix + selected + suffix + formContent.substring(end);
    setFormContent(newContent);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + prefix.length, end + prefix.length);
    }, 0);
  };

  const handleSave = async () => {
    if (!formTitle.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await notesApi.update(editing.id, { title: formTitle, content: formContent, category: formCategory || undefined });
      } else {
        await notesApi.create({ title: formTitle, content: formContent, category: formCategory || undefined });
      }
      cancel();
      loadNotes();
    } catch {
      // failed to save
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this note?')) return;
    try {
      await notesApi.delete(id);
      setNotesList(n => n.filter(note => note.id !== id));
    } catch {
      // failed to delete
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-serif text-ink">Planning Notes</h2>
          <p className="text-sm text-eco-text/60 mt-1">Your workspace for lesson planning notes</p>
        </div>
        <button onClick={startCreate}
          className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark text-white text-sm font-medium rounded-xl transition-colors">
          <Plus size={16} /> New note
        </button>
      </div>

      {(creating || editing) && (
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 mb-6 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-sans text-sm font-semibold text-ink">{editing ? 'Edit note' : 'New note'}</h3>
            <button onClick={cancel} className="p-1 rounded-lg hover:bg-sand/50"><X size={18} /></button>
          </div>
          <div className="space-y-3">
            <input value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="Note title"
              className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink font-medium focus:border-leaf" />
            <input value={formCategory} onChange={e => setFormCategory(e.target.value)} placeholder="Category (optional)"
              className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />

            <div className="border border-eco-border rounded-xl overflow-hidden">
              <div className="flex items-center gap-1 px-3 py-2 bg-sand/30 border-b border-eco-border">
                <button type="button" onClick={() => insertFormatting('**', '**')} className="p-1.5 rounded hover:bg-eco-card transition-colors" title="Bold">
                  <Bold size={14} className="text-eco-text/60" />
                </button>
                <button type="button" onClick={() => insertFormatting('*', '*')} className="p-1.5 rounded hover:bg-eco-card transition-colors" title="Italic">
                  <Italic size={14} className="text-eco-text/60" />
                </button>
                <button type="button" onClick={() => insertFormatting('\n- ', '')} className="p-1.5 rounded hover:bg-eco-card transition-colors" title="List">
                  <List size={14} className="text-eco-text/60" />
                </button>
                <span className="text-xs text-eco-text/30 ml-2">Markdown supported</span>
              </div>
              <textarea
                id="note-content"
                value={formContent}
                onChange={e => setFormContent(e.target.value)}
                rows={10}
                placeholder="Write your notes... Use **bold**, *italic*, and - lists"
                className="w-full px-4 py-3 text-sm text-ink focus:outline-none resize-none font-mono leading-relaxed"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button onClick={cancel} className="px-4 py-2 text-sm text-eco-text/60 hover:text-ink rounded-xl transition-colors">Cancel</button>
              <button onClick={handleSave} disabled={saving || !formTitle.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                {editing ? 'Update' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="animate-spin text-leaf" size={24} /></div>
      ) : notesList.length === 0 ? (
        <div className="text-center py-12 bg-eco-card rounded-2xl border border-eco-border">
          <StickyNote className="mx-auto text-eco-text/30 mb-3" size={40} />
          <p className="text-eco-text/50">No notes yet</p>
          <p className="text-sm text-eco-text/40 mt-1">Create your first planning note</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {notesList.map(note => (
            <div key={note.id}
              className="bg-eco-card rounded-2xl border border-eco-border p-5 hover:border-leaf/30 transition-colors cursor-pointer"
              onClick={() => setExpandedNote(expandedNote === note.id ? null : note.id)}
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="font-sans text-sm font-semibold text-ink">{note.title}</h4>
                  {note.category && <span className="text-xs text-eco-accent">{note.category}</span>}
                </div>
                <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                  <button onClick={() => startEdit(note)} className="p-1.5 rounded-lg text-eco-text/40 hover:text-ink hover:bg-sand/50 transition-colors">
                    <Edit3 size={14} />
                  </button>
                  <button onClick={() => handleDelete(note.id)} className="p-1.5 rounded-lg text-eco-text/40 hover:text-danger hover:bg-soft-rose/30 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <p className={`text-sm text-eco-text/60 whitespace-pre-wrap ${expandedNote === note.id ? '' : 'line-clamp-3'}`}>{note.content}</p>
              {note.updated_at && (
                <p className="text-xs text-eco-text/30 mt-3">{new Date(note.updated_at).toLocaleDateString()}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
