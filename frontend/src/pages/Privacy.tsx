import { Link } from 'react-router-dom';
import { ArrowLeft, Shield } from 'lucide-react';

export default function Privacy() {
  return (
    <div className="min-h-screen bg-paper">
      <div className="max-w-3xl mx-auto px-4 py-12 animate-fade-in">
        <Link to="/login" className="inline-flex items-center gap-1 text-sm text-eco-accent hover:text-eco-hover mb-8">
          <ArrowLeft size={14} /> Back to sign in
        </Link>

        <div className="flex items-center gap-3 mb-8">
          <Shield className="text-leaf" size={28} />
          <h1 className="text-3xl font-serif text-ink">Privacy Policy</h1>
        </div>

        <div className="bg-eco-card rounded-2xl border border-eco-border p-8 prose prose-sm max-w-none">
          <p className="text-eco-text/70 leading-relaxed">
            <strong>Effective Date:</strong> January 2026
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">1. Information We Collect</h2>
          <p className="text-eco-text/70 leading-relaxed">
            Guide collects the minimum information necessary to provide our educational services. For educators, this includes name, email address, and institution affiliation. For student accounts, we collect only the student's first name and a username, created by their educator with verified parental consent.
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">2. How We Use Information</h2>
          <p className="text-eco-text/70 leading-relaxed">
            All information is used solely to provide and improve Guide's educational services. We use AI-powered features through OpenAI's API, and all personally identifiable information is sanitized before being sent to external AI services. We never sell, share, or use student data for advertising purposes.
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">3. Data Protection for Students</h2>
          <p className="text-eco-text/70 leading-relaxed">
            Student accounts require verified parental or guardian consent before creation. Student interactions are monitored for safety, with concerning content flagged to their educator. Students can report concerns through a built-in safety reporting feature. We comply with the Australian Privacy Act 1988 and the Australian Privacy Principles (APPs).
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">4. Data Retention</h2>
          <p className="text-eco-text/70 leading-relaxed">
            Student records are retained for a maximum of 7 years. Child safety records are retained for 25 years in compliance with legal requirements. Educators may export or delete their data at any time through the Settings page.
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">5. Data Security</h2>
          <p className="text-eco-text/70 leading-relaxed">
            We use industry-standard security measures including encrypted passwords (bcrypt hashing), secure session management, inactivity timeouts, and audit logging for all actions involving student data.
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">6. Your Rights</h2>
          <p className="text-eco-text/70 leading-relaxed">
            You have the right to access, correct, export, and delete your data. Educators can manage these actions through the Settings page. For data deletion requests or privacy inquiries, please contact us through our contact form.
          </p>

          <h2 className="text-xl font-serif text-ink mt-6 mb-3">7. Contact</h2>
          <p className="text-eco-text/70 leading-relaxed">
            For privacy-related questions or concerns, please use our <Link to="/contact" className="text-eco-accent hover:text-eco-hover">contact form</Link> or email us directly.
          </p>
        </div>
      </div>
    </div>
  );
}
