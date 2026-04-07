import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Loader2, ArrowLeft, CheckCircle, Send } from 'lucide-react';

export default function Contact() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.post('/auth/contact', { name, email, message });
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-4">
      <div className="w-full max-w-lg animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-serif text-ink">Contact Us</h1>
          <p className="text-eco-text/60 mt-2">We'd love to hear from you</p>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
          {sent ? (
            <div className="text-center py-6">
              <CheckCircle className="mx-auto text-leaf mb-3" size={40} />
              <p className="text-ink font-medium">Message sent!</p>
              <p className="text-sm text-eco-text/60 mt-2">Thank you for reaching out. We'll get back to you soon.</p>
              <Link to="/login" className="inline-block mt-4 text-sm text-eco-accent hover:text-eco-hover">Back to sign in</Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger">{error}</div>
              )}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-ink mb-1.5">Name</label>
                  <input id="name" type="text" required value={name} onChange={e => setName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="Your name" />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">Email</label>
                  <input id="email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf"
                    placeholder="you@example.com" />
                </div>
                <div>
                  <label htmlFor="message" className="block text-sm font-medium text-ink mb-1.5">Message</label>
                  <textarea id="message" required value={message} onChange={e => setMessage(e.target.value)} rows={5}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf resize-none"
                    placeholder="How can we help?" />
                </div>
                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                  Send message
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
