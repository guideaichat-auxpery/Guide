import { useState, useEffect } from 'react';
import { studentsMgmt, dataApi } from '../lib/api';
import type { Student, Activity, SafetyAlert } from '../lib/types';
import { Loader2, Plus, Search, Users, ChevronRight, X, AlertTriangle, Clock, Shield, Share2 } from 'lucide-react';

export default function Students() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [detailTab, setDetailTab] = useState<'overview' | 'activities' | 'safety' | 'sharing'>('overview');
  const [activities, setActivities] = useState<Activity[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [formData, setFormData] = useState({ name: '', username: '', password: '', age_group: '6-9', consent_given: false });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [shareEmail, setShareEmail] = useState('');
  const [shareMsg, setShareMsg] = useState('');

  const loadStudents = async () => {
    setLoading(true);
    try {
      const res = await studentsMgmt.list();
      setStudents(res.students);
    } catch {
      // failed to load
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadStudents(); }, []);

  const loadStudentDetail = async (student: Student, tab: string) => {
    setLoadingDetail(true);
    try {
      if (tab === 'activities') {
        const res = await studentsMgmt.activities(student.id);
        setActivities(res.activities);
      } else if (tab === 'safety') {
        const res = await studentsMgmt.safetyAlerts(student.id);
        setAlerts(res.alerts);
      }
    } catch {
      // failed to load detail
    } finally {
      setLoadingDetail(false);
    }
  };

  const selectStudent = (student: Student) => {
    setSelectedStudent(student);
    setDetailTab('overview');
  };

  const handleTabChange = (tab: 'overview' | 'activities' | 'safety' | 'sharing') => {
    setDetailTab(tab);
    if (selectedStudent && (tab === 'activities' || tab === 'safety')) {
      loadStudentDetail(selectedStudent, tab);
    }
  };

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
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create student');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure? This will permanently delete this student and all their data.')) return;
    try {
      await studentsMgmt.delete(id);
      setStudents(s => s.filter(st => st.id !== id));
      if (selectedStudent?.id === id) setSelectedStudent(null);
    } catch {
      // failed to delete
    }
  };

  const handleGrantAccess = async () => {
    if (!shareEmail.trim() || !selectedStudent) return;
    try {
      await studentsMgmt.grantAccess(selectedStudent.id, { educator_email: shareEmail });
      setShareMsg('Access granted successfully');
      setShareEmail('');
    } catch (e) {
      setShareMsg(e instanceof Error ? e.message : 'Failed to grant access');
    }
  };

  const filtered = students.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.username.toLowerCase().includes(search.toLowerCase())
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

          <div className="flex gap-2 mb-6 flex-wrap">
            {(['overview', 'activities', 'safety', 'sharing'] as const).map(tab => (
              <button key={tab} onClick={() => handleTabChange(tab)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors capitalize ${
                  detailTab === tab ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-sand/30 border border-eco-border text-eco-text/70 hover:bg-sand/50'
                }`}>
                {tab === 'safety' ? 'Safety Alerts' : tab}
              </button>
            ))}
          </div>

          {detailTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-sand/20 rounded-xl">
                <h4 className="font-sans text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-2">Details</h4>
                <p className="text-sm text-ink">Age Group: {selectedStudent.age_group || 'Not set'}</p>
                <p className="text-sm text-ink mt-1">Created: {selectedStudent.created_at ? new Date(selectedStudent.created_at).toLocaleDateString() : 'N/A'}</p>
              </div>
              <div className="p-4 bg-sky/20 rounded-xl">
                <h4 className="font-sans text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-2">Learning Journey</h4>
                <p className="text-sm text-eco-text/60 italic">Track student progress across subjects</p>
              </div>
            </div>
          )}

          {detailTab === 'activities' && (
            <div>
              {loadingDetail ? (
                <div className="flex justify-center py-8"><Loader2 className="animate-spin text-leaf" size={24} /></div>
              ) : activities.length === 0 ? (
                <div className="text-center py-8">
                  <Clock className="mx-auto text-eco-text/30 mb-2" size={32} />
                  <p className="text-sm text-eco-text/50">No recent activities</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {activities.map(act => (
                    <div key={act.id} className="p-3 bg-sand/20 rounded-xl flex items-center gap-3">
                      <Clock size={14} className="text-eco-text/40 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-ink">{act.type}{act.subject ? ` — ${act.subject}` : ''}</p>
                        {act.created_at && <p className="text-xs text-eco-text/40">{new Date(act.created_at).toLocaleString()}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {detailTab === 'safety' && (
            <div>
              {loadingDetail ? (
                <div className="flex justify-center py-8"><Loader2 className="animate-spin text-leaf" size={24} /></div>
              ) : alerts.length === 0 ? (
                <div className="text-center py-8">
                  <Shield className="mx-auto text-leaf/40 mb-2" size={32} />
                  <p className="text-sm text-eco-text/50">No safety alerts</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {alerts.map(alert => (
                    <div key={alert.id} className="p-3 bg-soft-rose/20 border border-danger/10 rounded-xl">
                      <div className="flex items-center gap-2 mb-1">
                        <AlertTriangle size={14} className="text-danger" />
                        <span className="text-xs font-medium text-danger uppercase">{alert.status}</span>
                        {alert.created_at && <span className="text-xs text-eco-text/40 ml-auto">{new Date(alert.created_at).toLocaleString()}</span>}
                      </div>
                      <p className="text-sm text-ink">{alert.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {detailTab === 'sharing' && (
            <div className="max-w-md">
              <div className="flex items-center gap-2 mb-4">
                <Share2 size={18} className="text-leaf" />
                <h3 className="font-sans text-sm font-semibold text-ink">Share Access</h3>
              </div>
              <p className="text-sm text-eco-text/60 mb-4">Grant another educator access to this student's data.</p>
              <div className="flex gap-2">
                <input
                  value={shareEmail}
                  onChange={e => { setShareEmail(e.target.value); setShareMsg(''); }}
                  placeholder="educator@school.edu"
                  className="flex-1 px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                />
                <button onClick={handleGrantAccess} disabled={!shareEmail.trim()}
                  className="px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
                  Grant
                </button>
              </div>
              {shareMsg && <p className={`mt-2 text-sm ${shareMsg.includes('Failed') ? 'text-danger' : 'text-leaf-dark'}`}>{shareMsg}</p>}
            </div>
          )}
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
          {filtered.map(s => (
            <button key={s.id} onClick={() => selectStudent(s)}
              className="w-full flex items-center gap-3 p-4 bg-eco-card rounded-xl border border-eco-border hover:border-leaf/40 transition-colors text-left">
              <div className="w-9 h-9 rounded-full bg-sky/30 flex items-center justify-center text-ink font-semibold text-sm">
                {s.name.charAt(0).toUpperCase()}
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
