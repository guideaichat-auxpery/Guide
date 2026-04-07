import { useState, useEffect } from 'react';
import { schools, api } from '../lib/api';
import type { Educator, SchoolInfo } from '../lib/types';
import { Loader2, Users, Building2, Search, UserX, Copy, CheckCircle, KeyRound, Shield } from 'lucide-react';

interface UserLookupResult {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at?: string;
}

export default function SchoolAdmin() {
  const [school, setSchool] = useState<SchoolInfo | null>(null);
  const [educators, setEducators] = useState<Educator[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'educators' | 'users'>('overview');
  const [copied, setCopied] = useState(false);

  const [lookupEmail, setLookupEmail] = useState('');
  const [lookupResult, setLookupResult] = useState<UserLookupResult | null>(null);
  const [lookupError, setLookupError] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);

  const [resetEmail, setResetEmail] = useState('');
  const [resetMsg, setResetMsg] = useState('');
  const [resetLoading, setResetLoading] = useState(false);

  const loadSchool = async () => {
    setLoading(true);
    try {
      const s = await schools.mine();
      setSchool(s);
      if (s.id) {
        const res = await schools.educators(s.id);
        setEducators(res.educators);
      }
    } catch {
      // no school
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSchool(); }, []);

  const copyCode = () => {
    if (school?.school_code) {
      navigator.clipboard.writeText(school.school_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const removeEducator = async (educatorId: string) => {
    if (!school || !confirm('Remove this educator from the school?')) return;
    try {
      await schools.removeEducator(school.id, educatorId);
      setEducators(e => e.filter(ed => ed.id !== educatorId));
    } catch {
      // failed
    }
  };

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupEmail.trim()) return;
    setLookupLoading(true);
    setLookupError('');
    setLookupResult(null);
    try {
      const res = await api.get<UserLookupResult>(`/admin/users/lookup?email=${encodeURIComponent(lookupEmail)}`);
      setLookupResult(res);
    } catch (e) {
      setLookupError(e instanceof Error ? e.message : 'User not found');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleAdminResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetEmail.trim()) return;
    setResetLoading(true);
    setResetMsg('');
    try {
      const res = await api.post<{ message: string }>('/admin/users/reset-password', { email: resetEmail });
      setResetMsg(res.message || 'Password reset email sent successfully.');
      setResetEmail('');
    } catch (e) {
      setResetMsg(e instanceof Error ? e.message : 'Failed to send reset email');
    } finally {
      setResetLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12 animate-fade-in">
        <Loader2 className="animate-spin text-leaf" size={24} />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h2 className="text-2xl font-serif text-ink mb-1">School Administration</h2>
      <p className="text-sm text-eco-text/60 mb-6">Manage your school, educators, and users</p>

      <div className="flex gap-2 mb-6 flex-wrap">
        {(['overview', 'educators', 'users'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors capitalize ${
              tab === t ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-sand/30 border border-eco-border text-eco-text/70 hover:bg-sand/50'
            }`}>
            {t === 'users' ? 'User Management' : t}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-4">
          <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <Building2 className="text-leaf" size={22} />
              <h3 className="text-lg font-serif text-ink">{school?.name || 'Your School'}</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-sand/20 rounded-xl">
                <p className="text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-1">School Type</p>
                <p className="text-sm text-ink">{school?.school_type || 'Montessori'}</p>
              </div>
              <div className="p-4 bg-sand/20 rounded-xl">
                <p className="text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-1">Educators</p>
                <p className="text-sm text-ink">{educators.length} member{educators.length !== 1 ? 's' : ''}</p>
              </div>
            </div>
            {school?.school_code && (
              <div className="mt-4 p-4 bg-sky/10 rounded-xl">
                <p className="text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-1">Invite Code</p>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-mono text-ink tracking-wider">{school.school_code}</span>
                  <button onClick={copyCode}
                    className="p-1.5 rounded-lg hover:bg-sky/20 transition-colors">
                    {copied ? <CheckCircle size={16} className="text-leaf" /> : <Copy size={16} className="text-eco-text/40" />}
                  </button>
                </div>
                <p className="text-xs text-eco-text/40 mt-1">Share this code with educators to join your school</p>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'educators' && (
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users size={18} className="text-leaf" />
            <h3 className="font-sans text-sm font-semibold text-ink">School Educators</h3>
          </div>
          {educators.length === 0 ? (
            <p className="text-sm text-eco-text/50 italic">No educators have joined yet. Share the invite code to get started.</p>
          ) : (
            <div className="space-y-2">
              {educators.map(ed => (
                <div key={ed.id} className="flex items-center gap-3 p-3 bg-sand/20 rounded-xl">
                  <div className="w-9 h-9 rounded-full bg-leaf/15 flex items-center justify-center text-leaf-dark font-semibold text-sm">
                    {ed.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-ink truncate">{ed.name}</p>
                    <p className="text-xs text-eco-text/40">{ed.email} · {ed.role}</p>
                  </div>
                  <button onClick={() => removeEducator(ed.id)}
                    className="p-1.5 rounded-lg text-eco-text/30 hover:text-danger hover:bg-soft-rose/30 transition-colors" title="Remove">
                    <UserX size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'users' && (
        <div className="space-y-6">
          <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
            <div className="flex items-center gap-2 mb-4">
              <Search size={18} className="text-leaf" />
              <h3 className="font-sans text-sm font-semibold text-ink">User Lookup</h3>
            </div>
            <form onSubmit={handleLookup} className="flex gap-2 mb-4">
              <input value={lookupEmail} onChange={e => setLookupEmail(e.target.value)}
                placeholder="user@example.com"
                className="flex-1 px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              <button type="submit" disabled={lookupLoading || !lookupEmail.trim()}
                className="px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2">
                {lookupLoading && <Loader2 size={14} className="animate-spin" />}
                Lookup
              </button>
            </form>
            {lookupError && <p className="text-sm text-danger">{lookupError}</p>}
            {lookupResult && (
              <div className="p-4 bg-sand/20 rounded-xl">
                <p className="text-sm font-medium text-ink">{lookupResult.name}</p>
                <p className="text-xs text-eco-text/50">{lookupResult.email} · Role: {lookupResult.role}</p>
                {lookupResult.created_at && (
                  <p className="text-xs text-eco-text/40 mt-1">Joined: {new Date(lookupResult.created_at).toLocaleDateString()}</p>
                )}
              </div>
            )}
          </div>

          <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
            <div className="flex items-center gap-2 mb-4">
              <KeyRound size={18} className="text-leaf" />
              <h3 className="font-sans text-sm font-semibold text-ink">Admin Password Reset</h3>
            </div>
            <p className="text-sm text-eco-text/60 mb-3">Send a password reset email to any user in your school.</p>
            <form onSubmit={handleAdminResetPassword} className="flex gap-2">
              <input value={resetEmail} onChange={e => { setResetEmail(e.target.value); setResetMsg(''); }}
                placeholder="user@example.com"
                className="flex-1 px-4 py-2 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              <button type="submit" disabled={resetLoading || !resetEmail.trim()}
                className="px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2">
                {resetLoading && <Loader2 size={14} className="animate-spin" />}
                <Shield size={14} />
                Reset
              </button>
            </form>
            {resetMsg && (
              <p className={`mt-2 text-sm ${resetMsg.includes('Failed') ? 'text-danger' : 'text-leaf-dark'}`}>{resetMsg}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
