import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function Login() {
  const [tab, setTab] = useState<'educator' | 'student'>('educator');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [studentPw, setStudentPw] = useState('');
  const { login, studentLogin, loading, error, clearError } = useAuth();
  const navigate = useNavigate();

  const handleEducatorLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch {}
  };

  const handleStudentLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await studentLogin(username, studentPw);
      navigate('/learn');
    } catch {}
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-serif text-ink">Guide</h1>
          <p className="text-eco-text/60 mt-2">Your prepared digital environment</p>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          <div className="flex rounded-xl bg-sand/40 p-1 mb-6">
            <button
              onClick={() => { setTab('educator'); clearError(); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${tab === 'educator' ? 'bg-eco-card text-ink shadow-sm' : 'text-eco-text/60 hover:text-ink'}`}
            >
              Educator
            </button>
            <button
              onClick={() => { setTab('student'); clearError(); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${tab === 'student' ? 'bg-eco-card text-ink shadow-sm' : 'text-eco-text/60 hover:text-ink'}`}
            >
              Student
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">
              {error}
            </div>
          )}

          {tab === 'educator' ? (
            <form onSubmit={handleEducatorLogin} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">Email</label>
                <input
                  id="email" type="email" required value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                  placeholder="you@school.edu"
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-ink mb-1.5">Password</label>
                <input
                  id="password" type="password" required value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                  placeholder="Enter your password"
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                {loading && <Loader2 size={16} className="animate-spin" />}
                Sign in
              </button>
              <div className="flex justify-between text-sm">
                <Link to="/forgot-password" className="text-eco-accent hover:text-eco-hover transition-colors">
                  Forgot password?
                </Link>
                <Link to="/signup" className="text-eco-accent hover:text-eco-hover transition-colors">
                  Create account
                </Link>
              </div>
            </form>
          ) : (
            <form onSubmit={handleStudentLogin} className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-ink mb-1.5">Username</label>
                <input
                  id="username" type="text" required value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                  placeholder="Your username"
                />
              </div>
              <div>
                <label htmlFor="student-pw" className="block text-sm font-medium text-ink mb-1.5">Password</label>
                <input
                  id="student-pw" type="password" required value={studentPw}
                  onChange={e => setStudentPw(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                  placeholder="Your password"
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full py-2.5 bg-sky hover:bg-sky/80 disabled:opacity-50 text-ink font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                {loading && <Loader2 size={16} className="animate-spin" />}
                Start learning
              </button>
            </form>
          )}
        </div>

        <div className="text-center mt-6">
          <Link to="/join-school" className="text-sm text-eco-accent hover:text-eco-hover transition-colors">
            Join a school with invite code
          </Link>
        </div>
      </div>
    </div>
  );
}
