import { useState, useEffect } from 'react';
import ChatInterface from '../components/ChatInterface';
import { tools, type ChatMessage } from '../lib/api';
import { Loader2 } from 'lucide-react';

interface CompanionCard {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: string;
}

const defaultCards: CompanionCard[] = [
  { id: 'philosophy', title: 'Montessori Philosophy', description: 'Core principles and foundations', icon: '🌱', category: 'Foundation' },
  { id: 'prepared_environment', title: 'Prepared Environment', description: 'Creating optimal learning spaces', icon: '🏠', category: 'Foundation' },
  { id: 'observation', title: 'Observation', description: 'Techniques for observing children', icon: '👁️', category: 'Practice' },
  { id: 'practical_life', title: 'Practical Life', description: 'Daily living exercises', icon: '🧹', category: 'Curriculum' },
  { id: 'sensorial', title: 'Sensorial', description: 'Sensory exploration materials', icon: '✋', category: 'Curriculum' },
  { id: 'mathematics', title: 'Mathematics', description: 'Concrete to abstract math', icon: '🔢', category: 'Curriculum' },
  { id: 'language', title: 'Language', description: 'Reading, writing, communication', icon: '📖', category: 'Curriculum' },
  { id: 'cultural', title: 'Cultural Studies', description: 'Geography, science, history', icon: '🌍', category: 'Curriculum' },
  { id: 'cosmic_education', title: 'Cosmic Education', description: 'Interconnectedness of knowledge', icon: '✨', category: 'Philosophy' },
  { id: 'peace_education', title: 'Peace Education', description: 'Conflict resolution and community', icon: '🕊️', category: 'Philosophy' },
  { id: 'mixed_age', title: 'Mixed-Age Groups', description: 'Multi-age classroom dynamics', icon: '👨‍👩‍👧‍👦', category: 'Practice' },
  { id: 'assessment', title: 'Assessment', description: 'Authentic evaluation methods', icon: '📋', category: 'Practice' },
  { id: 'parent_partnership', title: 'Parent Partnership', description: 'Family engagement strategies', icon: '🤝', category: 'Community' },
  { id: 'transitions', title: 'Transitions', description: 'Supporting developmental changes', icon: '🦋', category: 'Practice' },
  { id: 'independence', title: 'Independence', description: 'Fostering self-directed learning', icon: '🌟', category: 'Philosophy' },
];

export default function Companion() {
  const [selectedCard, setSelectedCard] = useState<CompanionCard | null>(null);
  const [cards] = useState<CompanionCard[]>(defaultCards);

  if (selectedCard) {
    return (
      <div className="animate-fade-in">
        <button
          onClick={() => setSelectedCard(null)}
          className="mb-4 text-sm text-eco-accent hover:text-eco-hover transition-colors"
        >
          ← Back to topics
        </button>
        <ChatInterface
          title={`${selectedCard.icon} ${selectedCard.title}`}
          subtitle={selectedCard.description}
          placeholder={`Ask about ${selectedCard.title.toLowerCase()}...`}
          welcomeMessage={`Welcome to the ${selectedCard.title} area. I'm here to help you explore ${selectedCard.description.toLowerCase()}. What would you like to discuss?`}
          onSend={async (message, history) => {
            const res = await tools.companionChat({ message, history, card_id: selectedCard.id });
            return res.response;
          }}
        />
      </div>
    );
  }

  const categories = [...new Set(cards.map(c => c.category))];

  return (
    <div className="animate-fade-in">
      <h2 className="text-2xl font-serif text-ink mb-1">Montessori Companion</h2>
      <p className="text-sm text-eco-text/60 mb-6">Explore 15 areas of Montessori practice with your AI companion</p>

      {categories.map(category => (
        <div key={category} className="mb-6">
          <h3 className="font-sans text-xs font-semibold text-eco-text/50 uppercase tracking-wider mb-3">{category}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {cards.filter(c => c.category === category).map(card => (
              <button
                key={card.id}
                onClick={() => setSelectedCard(card)}
                className="text-left bg-eco-card rounded-2xl border border-eco-border p-4 hover:border-leaf/40 hover:shadow-sm transition-all duration-200"
              >
                <div className="text-2xl mb-2">{card.icon}</div>
                <h4 className="font-sans text-sm font-semibold text-ink">{card.title}</h4>
                <p className="text-xs text-eco-text/60 mt-1">{card.description}</p>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
