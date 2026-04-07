import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  BookOpen, MessageCircle, Sparkles, GraduationCap, BookMarked,
  Users, StickyNote, ArrowRight
} from 'lucide-react';

const tools = [
  { to: '/lesson-planning', icon: BookOpen, label: 'Lesson Planning', desc: 'Generate plans, align curriculum, differentiate lessons', color: 'bg-sky/30 text-ink' },
  { to: '/companion', icon: MessageCircle, label: 'Montessori Companion', desc: 'Explore 15 areas of Montessori practice', color: 'bg-leaf/15 text-leaf-dark' },
  { to: '/great-stories', icon: BookMarked, label: 'Great Stories', desc: 'Create and discover Montessori Great Stories', color: 'bg-clay/30 text-ink' },
  { to: '/imaginarium', icon: Sparkles, label: 'Imaginarium', desc: 'Creative ideation for your classroom', color: 'bg-soft-rose/40 text-ink' },
  { to: '/pd-expert', icon: GraduationCap, label: 'PD Expert', desc: 'Professional development guidance', color: 'bg-sand text-ink' },
  { to: '/students', icon: Users, label: 'Students', desc: 'Manage student profiles and progress', color: 'bg-sky/20 text-ink' },
  { to: '/planning-notes', icon: StickyNote, label: 'Planning Notes', desc: 'Your workspace for lesson notes', color: 'bg-leaf/10 text-leaf-dark' },
];

export default function Dashboard() {
  const { user } = useAuth();
  const displayName = user && 'name' in user ? user.name.split(' ')[0] : 'Educator';

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-3xl font-serif text-ink">Welcome back, {displayName}</h2>
        <p className="text-eco-text/60 mt-2">What would you like to work on today?</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {tools.map(tool => (
          <Link
            key={tool.to}
            to={tool.to}
            className="group bg-eco-card rounded-2xl border border-eco-border p-5 hover:border-leaf/40 hover:shadow-sm transition-all duration-200"
          >
            <div className={`w-10 h-10 rounded-xl ${tool.color} flex items-center justify-center mb-3`}>
              <tool.icon size={20} />
            </div>
            <h3 className="font-sans text-base font-semibold text-ink mb-1">{tool.label}</h3>
            <p className="text-sm text-eco-text/60 leading-relaxed">{tool.desc}</p>
            <div className="mt-3 flex items-center gap-1 text-xs font-medium text-eco-accent group-hover:text-eco-hover transition-colors">
              Open <ArrowRight size={12} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
