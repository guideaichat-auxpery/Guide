import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { auth, setToken } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, ArrowLeft, Building2 } from 'lucide-react';

export default function SchoolSetup() {
  const { user, refreshSession } = useAuth();
  const navigate = useNavigate();

  const isLoggedInEducator =
    !!user && 'email' in user && (!('user_type' in user) || user.user_type !== 'student');
  const existingSchoolId =
    user && 'school_id' in user ? (user as { school_id?: string | number }).school_id : undefined;

  const [schoolName, setSchoolName] = useState('');
  const [adminName, setAdminName] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (isLoggedInEducator && existingSchoolId) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-4">
        <div className="w-full max-w-md animate-fade-in text-center">
          <Building2 className="mx-auto text-leaf mb-3" size={36} />
          <h1 className="text-3xl font-serif text-ink mb-2">You already have a school</h1>
          <p className="text-eco-text/60 mb-6">
            Manage it from the School Admin section.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-leaf hover:bg-leaf-dark text-white font-medium rounded-xl transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!schoolName.trim()) {
      setError('Please enter a school name.');
      return;
    }
    if (!isLoggedInEducator) {
      if (adminPassword !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (adminPassword.length < 12) {
        setError('Password must be at least 12 characters');
        return;
      }
    }
    setLoading(true);
    setError('');
    try {
      const payload: {
        school_name: string;
        admin_email?: string;
        admin_password?: string;
        admin_name?: string;
        confirm_password?: string;
      } = { school_name: schoolName.trim() };
      if (!isLoggedInEducator) {
        payload.admin_email = adminEmail;
        payload.admin_password = adminPassword;
        payload.admin_name = adminName;
        payload.confirm_password = confirmPassword;
      }
      const res = await auth.setupSchool(payload);
      if (res.token) setToken(res.token);
      await refreshSession();
      const created = res.user as { school_name?: string; school_invite_code?: string };
      navigate('/dashboard', {
        replace: true,
        state: {
          newSchool: {
            name: created.school_name || schoolName.trim(),
            inviteCode: created.school_invite_code || '',
          },
        },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to set up school');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <Building2 className="mx-auto text-leaf mb-3" size={36} />
          <h1 className="text-3xl font-serif text-ink">Set Up Your School</h1>
          <p className="text-eco-text/60 mt-2">
            {isLoggedInEducator
              ? 'Create a school under your existing account and get an invite code to share with educators.'
              : 'Create your school account and get an invite code to share with your educators.'}
          </p>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {error && <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="schoolName" className="block text-sm font-medium text-ink mb-1.5">School name</label>
              <input id="schoolName" type="text" required value={schoolName} onChange={e => setSchoolName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                placeholder="e.g. Wairoa Montessori" />
              <p className="text-xs text-eco-text/50 mt-1">This is how your school will appear to educators who join.</p>
            </div>
            {!isLoggedInEducator && (
              <>
                <div>
                  <label htmlFor="adminName" className="block text-sm font-medium text-ink mb-1.5">Your full name</label>
                  <input id="adminName" type="text" required value={adminName} onChange={e => setAdminName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="Maria Montessori" />
                </div>
                <div>
                  <label htmlFor="adminEmail" className="block text-sm font-medium text-ink mb-1.5">Admin email</label>
                  <input id="adminEmail" type="email" required value={adminEmail} onChange={e => setAdminEmail(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="you@school.edu" />
                </div>
                <div>
                  <label htmlFor="adminPassword" className="block text-sm font-medium text-ink mb-1.5">Password</label>
                  <input id="adminPassword" type="password" required value={adminPassword} onChange={e => setAdminPassword(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="At least 12 characters" />
                </div>
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-ink mb-1.5">Confirm password</label>
                  <input id="confirmPassword" type="password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="Repeat your password" />
                </div>
              </>
            )}
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading && <Loader2 size={16} className="animate-spin" />}
              Create School
            </button>
          </form>
          {!isLoggedInEducator && (
            <div className="mt-4 text-center">
              <Link to="/login" className="inline-flex items-center gap-1 text-sm text-eco-accent hover:text-eco-hover">
                <ArrowLeft size={14} /> Back to sign in
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
