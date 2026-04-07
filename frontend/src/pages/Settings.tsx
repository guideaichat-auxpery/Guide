import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { users, auth as authApi, schools, data as dataApi } from '../lib/api';
import { Loader2, Save, Shield, Download, Users, AlertTriangle } from 'lucide-react';

export default function Settings() {
  const { user, isAdmin, isStudent, logout } = useAuth();
  const [name, setName] = useState('');
  const [institution, setInstitution] = useState('');
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [saving, setSaving] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [pwMessage, setPwMessage] = useState('');
  const [schoolInfo, setSchoolInfo] = useState<any>(null);
  const [educators, setEducators] = useState<any[]>([]);
  const [tab, setTab] = useState<'profile' | 'security' | 'school' | 'data'>('profile');

  useEffect(() => {
    if (user && 'name' in user) {
      setName(user.name || '');
      setInstitution((user as any).institution || '');
    }
  }, [user]);

  useEffect(() => {
    if (isAdmin && tab === 'school') {
      schools.mine().then((info: any) => {
        setSchoolInfo(info);
        if (info?.id) schools.educators(info.id).then((r: any) => setEducators(r.educators || [])).catch(() => {});
      }).catch(() => {});
    }
  }, [isAdmin, tab]);

  const handleProfileSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await users.updateMe({ name, institution });
      setMessage('Profile updated');
    } catch (e: any) {
      setMessage(e.message || 'Failed to update');
    } finally { setSaving(false); }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPw.length < 6) { setPwMessage('Password must be at least 6 characters'); return; }
    setPwSaving(true);
    setPwMessage('');
    try {
      await authApi.changePassword(currentPw, newPw);
      setPwMessage('Password changed successfully');
      setCurrentPw('');
      setNewPw('');
    } catch (e: any) {
      setPwMessage(e.message || 'Failed to change password');
    } finally { setPwSaving(false); }
  };

  const handleExportData = async () => {
    try {
      const data = await dataApi.export();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'guide-data-export.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure you want to delete your account? This cannot be undone.')) return;
    try {
      await users.deleteAccount();
      await logout();
    } catch {}
  };

  const tabs = [
    { key: 'profile' as const, label: 'Profile' },
    { key: 'security' as const, label: 'Security' },
    ...(!isStudent ? [{ key: 'data' as const, label: 'Data & Privacy' }] : []),
    ...(isAdmin ? [{ key: 'school' as const, label: 'School Admin' }] : []),
  ];

  return (
    <div className="animate-fade-in">
      <h2 className="text-2xl font-serif text-ink mb-6">Settings</h2>

      <div className="flex gap-2 mb-6 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
        {tab === 'profile' && (
          <div className="space-y-4 max-w-md">
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Name</label>
              <input value={name} onChange={e => setName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
            </div>
            {!isStudent && (
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Institution</label>
                <input value={institution} onChange={e => setInstitution(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                  placeholder="Your school or organization" />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Email</label>
              <input value={user && 'email' in user ? user.email : ''} readOnly
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-sand/30 text-sm text-eco-text/60" />
            </div>
            {message && <p className={`text-sm ${message.includes('Failed') ? 'text-danger' : 'text-leaf-dark'}`}>{message}</p>}
            <button onClick={handleProfileSave} disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save changes
            </button>
          </div>
        )}

        {tab === 'security' && (
          <div className="max-w-md">
            <div className="flex items-center gap-2 mb-4">
              <Shield size={18} className="text-leaf" />
              <h3 className="font-sans text-sm font-semibold text-ink">Change Password</h3>
            </div>
            <form onSubmit={handlePasswordChange} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Current password</label>
                <input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} required
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">New password</label>
                <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} required
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
              {pwMessage && <p className={`text-sm ${pwMessage.includes('Failed') ? 'text-danger' : 'text-leaf-dark'}`}>{pwMessage}</p>}
              <button type="submit" disabled={pwSaving}
                className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
                {pwSaving ? <Loader2 size={14} className="animate-spin" /> : <Shield size={14} />}
                Change password
              </button>
            </form>
          </div>
        )}

        {tab === 'data' && (
          <div className="space-y-6 max-w-md">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Download size={18} className="text-leaf" />
                <h3 className="font-sans text-sm font-semibold text-ink">Export Data</h3>
              </div>
              <p className="text-sm text-eco-text/60 mb-3">Download all your data in JSON format.</p>
              <button onClick={handleExportData}
                className="flex items-center gap-2 px-4 py-2 bg-eco-card border border-eco-border hover:bg-sand/50 text-sm font-medium text-ink rounded-xl transition-colors">
                <Download size={14} /> Export my data
              </button>
            </div>
            <div className="border-t border-eco-border pt-6">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={18} className="text-danger" />
                <h3 className="font-sans text-sm font-semibold text-danger">Danger Zone</h3>
              </div>
              <p className="text-sm text-eco-text/60 mb-3">Permanently delete your account and all associated data.</p>
              <button onClick={handleDeleteAccount}
                className="flex items-center gap-2 px-4 py-2 bg-danger/10 border border-danger/20 hover:bg-danger/20 text-sm font-medium text-danger rounded-xl transition-colors">
                <AlertTriangle size={14} /> Delete account
              </button>
            </div>
          </div>
        )}

        {tab === 'school' && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Users size={18} className="text-leaf" />
                <h3 className="font-sans text-sm font-semibold text-ink">School Information</h3>
              </div>
              {schoolInfo ? (
                <div className="p-4 bg-sand/20 rounded-xl text-sm text-ink space-y-1">
                  <p><span className="font-medium">Name:</span> {schoolInfo.name || schoolInfo.school_name || 'N/A'}</p>
                  <p><span className="font-medium">Code:</span> <code className="px-2 py-0.5 bg-eco-card rounded text-xs">{schoolInfo.code || schoolInfo.school_code || 'N/A'}</code></p>
                </div>
              ) : (
                <p className="text-sm text-eco-text/50">No school configured</p>
              )}
            </div>
            {educators.length > 0 && (
              <div>
                <h3 className="font-sans text-sm font-semibold text-ink mb-3">Educators ({educators.length})</h3>
                <div className="space-y-2">
                  {educators.map((ed: any) => (
                    <div key={ed.id || ed.email} className="flex items-center gap-3 p-3 bg-sand/20 rounded-xl">
                      <div className="w-8 h-8 rounded-full bg-leaf/20 flex items-center justify-center text-leaf-dark font-semibold text-xs">
                        {(ed.name || '?').charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-ink truncate">{ed.name}</div>
                        <div className="text-xs text-eco-text/50">{ed.email}</div>
                      </div>
                      <span className="text-xs px-2 py-0.5 bg-eco-card rounded-lg border border-eco-border">{ed.role || 'educator'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
