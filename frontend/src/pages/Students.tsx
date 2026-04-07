import { useState, useEffect } from 'react';
import { studentsMgmt } from '../lib/api';
import { Loader2, Plus, Search, Users, ChevronRight, X, AlertTriangle } from 'lucide-react';

export default function Students() {
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<any>(null);
  const [formData, setFormData] = useState({ name: '', username: '', password: '', age_group: '6-9', consent_given: false });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadStudents = async () => {
    setLoading(true);
    try {
      const res = await studentsMgmt.list();
      setStudents(res.students || []);
    } catch {} finally { setLoading(false); }
  };

  useEffect(() => { loadStudents(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.consent_given) { setError('Parental consent is required'); return; }
    setSaving(true);
    setError('');
    try {
      await studentsMgmt.create(formData);
      setShowCreate(false);
      setFormData({ name: '', username: '', password: '', age_group: '6-9', consent_given: false });
      loadStudents();
    } catch (e: any) {
      setError(e.message || 'Failed to create student');
    } finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure? This action cannot be undone.')) return;
    try {
      await studentsMgmt.delete(id);
      setStudents(s => s.filter(st => st.id !== id));
      if (selectedStudent?.id === id) setSelectedStudent(null);
    } catch {}
  };

  const filtered = students.filter(s =>
    (s.name || '').toLowerCase().includes(search.toLowerCase()) ||
    (s.username || '').toLowerCase().includes(search.toLowerCase())
  );

  if (selectedStudent) {
    return (
      <div className="animate-fade-in">
        <button onClick={() => setSelectedStudent(null)} className="mb-4 text-sm text-eco-accent hover:text-eco-hover transition-colors">
          ← Back to students
        </button>
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-serif text-ink">{selectedStudent.name}</h2>
              <p className="text-sm text-eco-text/60">@{selectedStudent.username} · {selectedStudent.age_group || 'No age group'}</p>
            </div>
            <button onClick={() => handleDelete(selectedStudent.id)}
              className="px-3 py-1.5 text-sm text-danger hover:bg-soft-rose/30 rounded-xl transition-colors">
              Delete student
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-sand/20 rounded-xl">
              <h4 className="font-sans text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-2">Details</h4>
              <p className="text-sm text-ink">Age Group: {selectedStudent.age_group || 'Not set'}</p>
              <p className="text-sm text-ink mt-1">Created: {selectedStudent.created_at ? new Date(selectedStudent.created_at).toLocaleDateString() : 'N/A'}</p>
            </div>
            <div className="p-4 bg-sky/20 rounded-xl">
              <h4 className="font-sans text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-2">Learning</h4>
              <p className="text-sm text-eco-text/60 italic">Learning journey data will appear here</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-serif text-ink">Students</h2>
          <p className="text-sm text-eco-text/60 mt-1">Manage student profiles and monitor progress</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark text-white text-sm font-medium rounded-xl transition-colors">
          <Plus size={16} /> Add student
        </button>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="bg-eco-card rounded-2xl border border-eco-border p-6 w-full max-w-md mx-4 shadow-xl animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-serif text-ink">Add Student</h3>
              <button onClick={() => setShowCreate(false)} className="p-1 rounded-lg hover:bg-sand/50"><X size={18} /></button>
            </div>
            {error && <div className="mb-3 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>}
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Name</label>
                <input value={formData.name} onChange={e => setFormData(f => ({ ...f, name: e.target.value }))} required
                  className="w-full px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Username</label>
                <input value={formData.username} onChange={e => setFormData(f => ({ ...f, username: e.target.value }))} required
                  className="w-full px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Password</label>
                <input type="password" value={formData.password} onChange={e => setFormData(f => ({ ...f, password: e.target.value }))} required
                  className="w-full px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1">Age group</label>
                <select value={formData.age_group} onChange={e => setFormData(f => ({ ...f, age_group: e.target.value }))}
                  className="w-full px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf">
                  <option value="3-6">3-6 (Primary)</option>
                  <option value="6-9">6-9 (Lower Elementary)</option>
                  <option value="9-12">9-12 (Upper Elementary)</option>
                  <option value="12-15">12-15 (Adolescent)</option>
                </select>
              </div>
              <label className="flex items-start gap-2 text-sm text-ink cursor-pointer">
                <input type="checkbox" checked={formData.consent_given}
                  onChange={e => setFormData(f => ({ ...f, consent_given: e.target.checked }))}
                  className="mt-0.5 rounded border-eco-border text-leaf focus:ring-leaf" />
                <span>I confirm parental/guardian consent has been obtained for this student's participation</span>
              </label>
              <button type="submit" disabled={saving}
                className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                {saving ? <><Loader2 size={16} className="animate-spin" /> Creating...</> : 'Create student'}
              </button>
            </form>
          </div>
        </div>
      )}

      <div className="mb-4 relative">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-eco-text/40" />
        <input value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-eco-border bg-eco-card text-sm text-ink focus:border-leaf"
          placeholder="Search students..." />
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="animate-spin text-leaf" size={24} /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 bg-eco-card rounded-2xl border border-eco-border">
          <Users className="mx-auto text-eco-text/30 mb-3" size={40} />
          <p className="text-eco-text/50">{search ? 'No students found' : 'No students yet'}</p>
          {!search && <p className="text-sm text-eco-text/40 mt-1">Add your first student to get started</p>}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((s: any) => (
            <button key={s.id} onClick={() => setSelectedStudent(s)}
              className="w-full flex items-center gap-3 p-4 bg-eco-card rounded-xl border border-eco-border hover:border-leaf/40 transition-colors text-left">
              <div className="w-9 h-9 rounded-full bg-sky/30 flex items-center justify-center text-ink font-semibold text-sm">
                {(s.name || '?').charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-ink truncate">{s.name}</div>
                <div className="text-xs text-eco-text/50">@{s.username} · {s.age_group || ''}</div>
              </div>
              <ChevronRight size={16} className="text-eco-text/30" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
