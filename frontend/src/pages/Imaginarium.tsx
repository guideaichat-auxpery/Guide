import ChatInterface from '../components/ChatInterface';
import { tools, type ChatMessage } from '../lib/api';

export default function Imaginarium() {
  return (
    <ChatInterface
      title="Imaginarium"
      subtitle="Creative ideation for your Montessori classroom"
      placeholder="Describe a creative challenge or idea you'd like to explore..."
      welcomeMessage="Welcome to the Imaginarium! I'm here to help you brainstorm creative ideas for your classroom. Whether it's a new activity, an interdisciplinary connection, or an innovative approach to a concept — let's explore together. What sparks your curiosity?"
      quickPrompts={[
        "Creative math activities",
        "Nature-based science projects",
        "Cross-curricular connections",
        "Classroom environment ideas",
      ]}
      onSend={async (message, history) => {
        const res = await tools.imaginariumChat({ message, history });
        return res.response;
      }}
    />
  );
}
