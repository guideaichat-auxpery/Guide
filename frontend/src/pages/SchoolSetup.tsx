import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { auth, schools, setToken } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, ArrowLeft, CheckCircle, Building2 } from 'lucide-react';

export default function SchoolSetup() {
  const [params] = useSearchParams();
  const tokenFromUrl = params.get('setup_token') || params.get('token') || '';
  const [setupToken, setSetupToken] = useState(tokenFromUrl);
  const [adminName, setAdminName] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [schoolCode, setSchoolCode] = useState('');
  const [schoolName, setSchoolName] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { refreshSession } = useAuth();

  useEffect(() => {
    setSetupToken(tokenFromUrl);
  }, [tokenFromUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!setupToken.trim()) {
      setError('A school setup token is required. Please use the link from your invitation email.');
      return;
    }
    if (adminPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (adminPassword.length < 12) {
      setError('Password must be at least 12 characters');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await auth.setupSchool({
        setup_token: setupToken,
        admin_email: adminEmail,
        admin_password: adminPassword,
        admin_name: adminName,
        confirm_password: confirmPassword,
      });
      setToken(res.token);
      await refreshSession();
      const created = res.user as { school_name?: string };
      const fallbackName = created.school_name || '';
      let resolvedName = fallbackName;
      let resolvedCode = '';
      try {
        const info = await schools.mine();
        resolvedCode = info?.invite_code || info?.code || info?.school_code || '';
        resolvedName = info?.name || fallbackName;
      } catch {
        // ignore — show success without code
      }
      setSchoolName(resolvedName);
      setSchoolCode(resolvedCode);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to set up school');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <Building2 className="mx-auto text-leaf mb-3" size={36} />
          <h1 className="text-3xl font-serif text-ink">Set Up Your School</h1>
          <p className="text-eco-text/60 mt-2">Claim your school account using the setup link from your invitation email</p>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {success ? (
            <div className="text-center py-4">
              <CheckCircle className="mx-auto text-leaf mb-3" size={40} />
              <p className="text-ink font-medium mb-2">School set up successfully!</p>
              {schoolName && (
                <p className="text-sm text-eco-text/60 mb-3">{schoolName}</p>
              )}
              {schoolCode ? (
                <div className="p-4 bg-sky/10 rounded-xl mb-4">
                  <p className="text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-1">Your School Invite Code</p>
                  <p className="text-2xl font-mono text-ink tracking-wider">{schoolCode}</p>
                  <p className="text-xs text-eco-text/40 mt-2">Share this code with educators so they can join your school</p>
                </div>
              ) : (
                <p className="text-sm text-eco-text/60 mb-4">You can find your school invite code under Settings → School Admin.</p>
              )}
              <button onClick={() => navigate('/dashboard')}
                className="w-full py-2.5 bg-leaf hover:bg-leaf-dark text-white font-medium rounded-xl transition-colors">
                Go to Dashboard
              </button>
            </div>
          ) : (
            <>
              {error && <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>}
              <form onSubmit={handleSubmit} className="space-y-4">
                {!tokenFromUrl && (
                  <div>
                    <label htmlFor="setupToken" className="block text-sm font-medium text-ink mb-1.5">Setup token</label>
                    <input id="setupToken" type="text" required value={setupToken} onChange={e => setSetupToken(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf font-mono"
                      placeholder="Paste the token from your invitation email" />
                    <p className="text-xs text-eco-text/50 mt-1">If you arrived from a setup link, this will be filled in automatically.</p>
                  </div>
                )}
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
                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  Create School Admin
                </button>
              </form>
            </>
          )}
          <div className="mt-4 text-center">
            <Link to="/login" className="inline-flex items-center gap-1 text-sm text-eco-accent hover:text-eco-hover">
              <ArrowLeft size={14} /> Back to sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
