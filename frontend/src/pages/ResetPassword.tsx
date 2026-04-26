import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { auth } from '../lib/api';
import { Loader2, CheckCircle } from 'lucide-react';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || params.get('reset_token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError('Passwords do not match'); return; }
    if (password.length < 12) { setError('Password must be at least 12 characters'); return; }
    setLoading(true);
    setError('');
    try {
      await auth.resetPassword({
        token,
        new_password: password,
        confirm_password: confirm,
      });
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {done ? (
            <div className="text-center py-4">
              <CheckCircle className="mx-auto text-leaf mb-3" size={40} />
              <p className="text-ink font-medium">Password reset successfully</p>
              <Link to="/login" className="inline-block mt-4 text-sm text-eco-accent hover:text-eco-hover">Sign in with your new password</Link>
            </div>
          ) : (
            <>
              <h2 className="text-2xl font-serif text-ink mb-4">Set new password</h2>
              {error && <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>}
              {!token && <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">Invalid or missing reset token.</div>}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="pw" className="block text-sm font-medium text-ink mb-1.5">New password</label>
                  <input id="pw" type="password" required value={password} onChange={e => setPassword(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
                </div>
                <div>
                  <label htmlFor="cpw" className="block text-sm font-medium text-ink mb-1.5">Confirm password</label>
                  <input id="cpw" type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
                </div>
                <button type="submit" disabled={loading || !token}
                  className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  Reset password
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
