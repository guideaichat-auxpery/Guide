import { useAuth } from '../contexts/AuthContext';
import ChatInterface from '../components/ChatInterface';
import { tools, PD_EXPERT_ALLOWED_EMAILS, type ChatMessage } from '../lib/api';
import { ShieldAlert } from 'lucide-react';

export default function PdExpert() {
  const { user } = useAuth();
  const userEmail = user && 'email' in user ? user.email : '';
  const hasAccess = PD_EXPERT_ALLOWED_EMAILS.includes(userEmail);

  if (!hasAccess) {
    return (
      <div className="animate-fade-in text-center py-16">
        <ShieldAlert className="mx-auto text-eco-text/30 mb-4" size={48} />
        <h2 className="text-2xl font-serif text-ink mb-2">Access Restricted</h2>
        <p className="text-eco-text/60 max-w-md mx-auto">
          The PD Expert is currently available by invitation only. Contact your administrator for access.
        </p>
      </div>
    );
  }

  return (
    <ChatInterface
      title="PD Expert"
      subtitle="Professional development guidance for Montessori educators"
      placeholder="Ask about professional development, training, or certification..."
      welcomeMessage="Hello! I'm the Professional Development Expert. I can help you with Montessori certification pathways, continuing education, reflective practice, and professional growth strategies. What area of your professional development would you like to explore?"
      quickPrompts={[
        "Montessori certification options",
        "Reflective practice techniques",
        "Observation skills development",
        "Building a professional portfolio",
      ]}
      onSend={async (message: string, history: ChatMessage[]) => {
        const res = await tools.pdExpertChat({ message, history });
        return res.response;
      }}
    />
  );
}
