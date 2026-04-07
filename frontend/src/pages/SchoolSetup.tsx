import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { auth } from '../lib/api';
import { Loader2, ArrowLeft, CheckCircle, Building2 } from 'lucide-react';

export default function SchoolSetup() {
  const [schoolName, setSchoolName] = useState('');
  const [schoolType, setSchoolType] = useState('montessori');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [schoolCode, setSchoolCode] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await auth.setupSchool({ school_name: schoolName, school_type: schoolType });
      setSchoolCode(res.school_code);
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
          <p className="text-eco-text/60 mt-2">Create your school account and invite educators</p>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {success ? (
            <div className="text-center py-4">
              <CheckCircle className="mx-auto text-leaf mb-3" size={40} />
              <p className="text-ink font-medium mb-2">School created successfully!</p>
              <div className="p-4 bg-sky/10 rounded-xl mb-4">
                <p className="text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-1">Your School Invite Code</p>
                <p className="text-2xl font-mono text-ink tracking-wider">{schoolCode}</p>
                <p className="text-xs text-eco-text/40 mt-2">Share this code with educators so they can join your school</p>
              </div>
              <button onClick={() => navigate('/dashboard')}
                className="w-full py-2.5 bg-leaf hover:bg-leaf-dark text-white font-medium rounded-xl transition-colors">
                Go to Dashboard
              </button>
            </div>
          ) : (
            <>
              {error && <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="schoolName" className="block text-sm font-medium text-ink mb-1.5">School name</label>
                  <input id="schoolName" type="text" required value={schoolName} onChange={e => setSchoolName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="e.g., Harmony Montessori School" />
                </div>
                <div>
                  <label htmlFor="schoolType" className="block text-sm font-medium text-ink mb-1.5">School type</label>
                  <select id="schoolType" value={schoolType} onChange={e => setSchoolType(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf">
                    <option value="montessori">Montessori</option>
                    <option value="montessori_primary">Montessori Primary (3-6)</option>
                    <option value="montessori_elementary">Montessori Elementary (6-12)</option>
                    <option value="montessori_adolescent">Montessori Adolescent (12-18)</option>
                    <option value="montessori_all_levels">Montessori All Levels</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  Create School
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
