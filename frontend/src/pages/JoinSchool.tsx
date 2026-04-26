import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { auth, setToken } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, ArrowLeft, CheckCircle } from 'lucide-react';

export default function JoinSchool() {
  const [code, setCode] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { refreshSession } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreeTerms) { setError('You must agree to the terms and conditions'); return; }
    if (password !== confirm) { setError('Passwords do not match'); return; }
    if (password.length < 12) { setError('Password must be at least 12 characters'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await auth.joinSchool({
        invite_code: code,
        email,
        password,
        full_name: fullName,
        confirm_password: confirm,
        agree_terms: agreeTerms,
      });
      setToken(res.token);
      await refreshSession();
      setSuccess(true);
      setTimeout(() => navigate('/dashboard'), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to join school');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-serif text-ink">Join a School</h1>
          <p className="text-eco-text/60 mt-2">Enter your school's invite code and create your educator account</p>
        </div>
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {success ? (
            <div className="text-center py-4">
              <CheckCircle className="mx-auto text-leaf mb-3" size={40} />
              <p className="text-ink font-medium">Successfully joined!</p>
              <p className="text-sm text-eco-text/60 mt-1">Redirecting to dashboard...</p>
            </div>
          ) : (
            <>
              {error && <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="code" className="block text-sm font-medium text-ink mb-1.5">School invite code</label>
                  <input id="code" type="text" required value={code} onChange={e => setCode(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink text-center tracking-wider uppercase placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="ABC123" />
                </div>
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-ink mb-1.5">Full name</label>
                  <input id="fullName" type="text" required value={fullName} onChange={e => setFullName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="Maria Montessori" />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">Email</label>
                  <input id="email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="you@school.edu" />
                  <p className="text-xs text-eco-text/50 mt-1">If you already have an account, enter its email and password to link it to this school.</p>
                </div>
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-ink mb-1.5">Password</label>
                  <input id="password" type="password" required value={password} onChange={e => setPassword(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="At least 12 characters" />
                </div>
                <div>
                  <label htmlFor="confirm" className="block text-sm font-medium text-ink mb-1.5">Confirm password</label>
                  <input id="confirm" type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="Repeat your password" />
                </div>
                <label className="flex items-start gap-2 text-sm text-ink cursor-pointer">
                  <input type="checkbox" checked={agreeTerms} onChange={e => setAgreeTerms(e.target.checked)}
                    className="mt-0.5 rounded border-eco-border text-leaf focus:ring-leaf" />
                  <span>
                    I agree to the <Link to="/privacy" className="text-eco-accent hover:text-eco-hover">privacy policy</Link> and terms of service.
                  </span>
                </label>
                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  Join school
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
