import { useState } from 'react';
import { Link } from 'react-router-dom';
import { auth } from '../lib/api';
import { Loader2, ArrowLeft, CheckCircle } from 'lucide-react';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await auth.forgotPassword(email);
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-serif text-ink">Reset Password</h1>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {sent ? (
            <div className="text-center py-4">
              <CheckCircle className="mx-auto text-leaf mb-3" size={40} />
              <p className="text-ink font-medium">Check your email</p>
              <p className="text-sm text-eco-text/60 mt-2">If an account exists for {email}, we've sent reset instructions.</p>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>
              )}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">Email address</label>
                  <input id="email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="you@school.edu" />
                </div>
                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  Send reset link
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
