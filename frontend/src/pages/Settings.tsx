import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { users, auth as authApi, schools, dataApi } from '../lib/api';
import type { SchoolInfo, Educator } from '../lib/types';
import { Loader2, Save, Shield, Download, Users, AlertTriangle, Mail, RefreshCw } from 'lucide-react';

export default function Settings() {
  const { user, isAdmin, isStudent, logout, refreshSession } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [institution, setInstitution] = useState('');
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [emailNew, setEmailNew] = useState('');
  const [emailPw, setEmailPw] = useState('');
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailMessage, setEmailMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [pwMessage, setPwMessage] = useState('');
  const [schoolInfo, setSchoolInfo] = useState<SchoolInfo | null>(null);
  const [educatorsList, setEducatorsList] = useState<Educator[]>([]);
  const [rotatingCode, setRotatingCode] = useState(false);
  const [rotateMessage, setRotateMessage] = useState('');
  const [rotateError, setRotateError] = useState(false);
  const [tab, setTab] = useState<'profile' | 'security' | 'school' | 'data'>('profile');

  useEffect(() => {
    if (user) {
      const u = user as { full_name?: string; institution_name?: string; email?: string };
      setFullName(u.full_name || '');
      setInstitution(u.institution_name || '');
      setEmailNew(u.email || '');
    }
  }, [user]);

  useEffect(() => {
    if (isAdmin && tab === 'school') {
      schools.mine().then(info => {
        setSchoolInfo(info);
        if (info?.id) {
          schools.educators(info.id).then(r => setEducatorsList(r.educators)).catch(() => {});
        }
      }).catch(() => {});
    }
  }, [isAdmin, tab]);

  const handleProfileSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await users.updateMe({ full_name: fullName, institution_name: institution });
      await refreshSession();
      setMessage('Profile updated');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Failed to update');
    } finally {
      setSaving(false);
    }
  };

  const handleEmailChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailSaving(true);
    setEmailMessage('');
    try {
      await users.updateEmail({ new_email: emailNew, current_password: emailPw });
      await refreshSession();
      setEmailPw('');
      setEmailMessage('Email updated successfully');
    } catch (err) {
      setEmailMessage(err instanceof Error ? err.message : 'Failed to update email');
    } finally {
      setEmailSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPw !== confirmPw) { setPwMessage('Passwords do not match'); return; }
    if (newPw.length < 12) { setPwMessage('Password must be at least 12 characters'); return; }
    setPwSaving(true);
    setPwMessage('');
    try {
      await authApi.changePassword({
        current_password: currentPw,
        new_password: newPw,
        confirm_password: confirmPw,
      });
      setPwMessage('Password changed successfully');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (e) {
      setPwMessage(e instanceof Error ? e.message : 'Failed to change password');
    } finally {
      setPwSaving(false);
    }
  };

  const handleExportData = async () => {
    try {
      const exportData = await dataApi.export();
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'guide-data-export.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // failed to export
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure you want to delete your account? This cannot be undone.')) return;
    if (!confirm('This will permanently delete all your data, students, notes, and conversations. Proceed?')) return;
    try {
      await users.deleteAccount();
      await logout();
      navigate('/login');
    } catch {
      // failed to delete
    }
  };

  const handleRotateInviteCode = async () => {
    if (!schoolInfo?.id) return;
    if (!confirm('Generate a new invite code? The current code will stop working immediately.')) return;
    setRotatingCode(true);
    setRotateMessage('');
    setRotateError(false);
    try {
      const res = await schools.rotateInviteCode(schoolInfo.id);
      setSchoolInfo(prev => prev ? { ...prev, invite_code: res.invite_code } : prev);
      setRotateMessage('New invite code generated');
      setRotateError(false);
    } catch (e) {
      setRotateMessage(e instanceof Error ? e.message : 'Failed to regenerate invite code');
      setRotateError(true);
    } finally {
      setRotatingCode(false);
    }
  };

  const handleRemoveEducator = async (educatorId: string) => {
    if (!schoolInfo?.id) return;
    if (!confirm('Remove this educator from the school?')) return;
    try {
      await schools.removeEducator(schoolInfo.id, educatorId);
      setEducatorsList(prev => prev.filter(e => e.id !== educatorId));
    } catch {
      // failed to remove
    }
  };

  const tabs = [
    { key: 'profile' as const, label: 'Profile' },
    { key: 'security' as const, label: 'Security' },
    ...(!isStudent ? [{ key: 'data' as const, label: 'Data & Privacy' }] : []),
    ...(isAdmin ? [{ key: 'school' as const, label: 'School Admin' }] : []),
  ];

  const currentEmail = user && 'email' in user ? (user as { email?: string }).email || '' : '';

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
          <div className="space-y-8 max-w-md">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Full name</label>
                <input value={fullName} onChange={e => setFullName(e.target.value)}
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
              {message && <p className={`text-sm ${message.toLowerCase().includes('fail') ? 'text-danger' : 'text-leaf-dark'}`}>{message}</p>}
              <button onClick={handleProfileSave} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Save changes
              </button>
            </div>

            {!isStudent && (
              <div className="border-t border-eco-border pt-6">
                <div className="flex items-center gap-2 mb-3">
                  <Mail size={18} className="text-leaf" />
                  <h3 className="font-sans text-sm font-semibold text-ink">Change Email</h3>
                </div>
                <p className="text-xs text-eco-text/60 mb-3">
                  Current email: <span className="font-medium text-ink">{currentEmail}</span>
                </p>
                <form onSubmit={handleEmailChange} className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-ink mb-1.5">New email</label>
                    <input type="email" required value={emailNew} onChange={e => setEmailNew(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-ink mb-1.5">Current password</label>
                    <input type="password" required value={emailPw} onChange={e => setEmailPw(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                      placeholder="Confirm with your current password" />
                  </div>
                  {emailMessage && <p className={`text-sm ${emailMessage.toLowerCase().includes('fail') || emailMessage.toLowerCase().includes('incorrect') || emailMessage.toLowerCase().includes('invalid') ? 'text-danger' : 'text-leaf-dark'}`}>{emailMessage}</p>}
                  <button type="submit" disabled={emailSaving || !emailPw || emailNew === currentEmail}
                    className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
                    {emailSaving ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
                    Update email
                  </button>
                </form>
              </div>
            )}
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
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                  placeholder="At least 12 characters" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Confirm new password</label>
                <input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} required
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
              {pwMessage && <p className={`text-sm ${pwMessage.toLowerCase().includes('success') ? 'text-leaf-dark' : 'text-danger'}`}>{pwMessage}</p>}
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
                <div className="p-4 bg-sand/20 rounded-xl text-sm text-ink space-y-2">
                  <p><span className="font-medium">Name:</span> {schoolInfo.name || schoolInfo.school_name || 'N/A'}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">Invite Code:</span>
                    <code className="px-2 py-0.5 bg-eco-card rounded text-xs font-mono">{schoolInfo.invite_code || schoolInfo.code || schoolInfo.school_code || 'N/A'}</code>
                    <button
                      onClick={handleRotateInviteCode}
                      disabled={rotatingCode}
                      className="flex items-center gap-1.5 px-2.5 py-1 bg-eco-card border border-eco-border hover:bg-sand/50 disabled:opacity-50 text-xs font-medium text-ink rounded-lg transition-colors"
                    >
                      {rotatingCode ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                      Regenerate
                    </button>
                  </div>
                  <p className="text-xs text-eco-text/60">Regenerating creates a new code and immediately disables the old one.</p>
                  {rotateMessage && (
                    <p className={`text-xs ${rotateError ? 'text-danger' : 'text-leaf-dark'}`}>{rotateMessage}</p>
                  )}
                  {schoolInfo.license_count !== undefined && (
                    <p><span className="font-medium">Seats:</span> {schoolInfo.educator_count || educatorsList.length} / {schoolInfo.license_count} used</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-eco-text/50">No school configured</p>
              )}
            </div>
            {educatorsList.length > 0 && (
              <div>
                <h3 className="font-sans text-sm font-semibold text-ink mb-3">Educators ({educatorsList.length})</h3>
                <div className="space-y-2">
                  {educatorsList.map(ed => (
                    <div key={ed.id} className="flex items-center gap-3 p-3 bg-sand/20 rounded-xl">
                      <div className="w-8 h-8 rounded-full bg-leaf/20 flex items-center justify-center text-leaf-dark font-semibold text-xs">
                        {(ed.full_name || ed.email || '?').charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-ink truncate">{ed.full_name || ed.email}</div>
                        <div className="text-xs text-eco-text/50">{ed.email}</div>
                      </div>
                      <span className="text-xs px-2 py-0.5 bg-eco-card rounded-lg border border-eco-border">{ed.role}</span>
                      <button
                        onClick={() => handleRemoveEducator(ed.id)}
                        className="text-xs text-danger/60 hover:text-danger transition-colors"
                      >
                        Remove
                      </button>
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
