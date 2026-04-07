import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { auth } from '../lib/api';
import { Loader2, ArrowLeft, CheckCircle } from 'lucide-react';

export default function JoinSchool() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await auth.joinSchool(code);
      setSuccess(true);
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Invalid invite code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-serif text-ink">Join a School</h1>
          <p className="text-eco-text/60 mt-2">Enter the invite code from your school administrator</p>
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
