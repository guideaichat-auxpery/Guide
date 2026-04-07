import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function Signup() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [localError, setLocalError] = useState('');
  const { signup, loading, error } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setLocalError('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters');
      return;
    }
    setLocalError('');
    try {
      await signup({ name, email, password });
      navigate('/dashboard');
    } catch {}
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-serif text-ink">Create Account</h1>
          <p className="text-eco-text/60 mt-2">Join Guide as an educator</p>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {displayError && (
            <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">
              {displayError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-ink mb-1.5">Full name</label>
              <input id="name" type="text" required value={name} onChange={e => setName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                placeholder="Maria Montessori" />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">Email</label>
              <input id="email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                placeholder="you@school.edu" />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-ink mb-1.5">Password</label>
              <input id="password" type="password" required value={password} onChange={e => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                placeholder="At least 6 characters" />
            </div>
            <div>
              <label htmlFor="confirm" className="block text-sm font-medium text-ink mb-1.5">Confirm password</label>
              <input id="confirm" type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                placeholder="Repeat your password" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading && <Loader2 size={16} className="animate-spin" />}
              Create account
            </button>
          </form>

          <div className="text-center mt-4 space-y-2">
            <p className="text-sm text-eco-text/60">
              Already have an account? <Link to="/login" className="text-eco-accent hover:text-eco-hover">Sign in</Link>
            </p>
            <p className="text-xs text-eco-text/40">
              Want to register a school? <Link to="/school-setup" className="text-eco-accent hover:text-eco-hover">Set up your school</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
