import ChatInterface from '../components/ChatInterface';
import { tools, type ChatMessage } from '../lib/api';

export default function PdExpert() {
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
      onSend={async (message, history) => {
        const res = await tools.pdExpertChat({ message, history });
        return res.response;
      }}
    />
  );
}
