import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { schools } from '../lib/api';
import {
  BookOpen, MessageCircle, Sparkles, GraduationCap, BookMarked,
  Users, StickyNote, ArrowRight, Building2, AlertCircle
} from 'lucide-react';

const toolsList = [
  { to: '/lesson-planning', icon: BookOpen, label: 'Lesson Planning', desc: 'Generate plans, align curriculum, differentiate lessons', color: 'bg-sky/30 text-ink' },
  { to: '/companion', icon: MessageCircle, label: 'Montessori Companion', desc: 'Explore 15 areas of Montessori practice', color: 'bg-leaf/15 text-leaf-dark' },
  { to: '/great-stories', icon: BookMarked, label: 'Great Stories', desc: 'Create and discover Montessori Great Stories', color: 'bg-clay/30 text-ink' },
  { to: '/imaginarium', icon: Sparkles, label: 'Imaginarium', desc: 'Creative ideation for your classroom', color: 'bg-soft-rose/40 text-ink' },
  { to: '/pd-expert', icon: GraduationCap, label: 'PD Expert', desc: 'Professional development guidance', color: 'bg-sand text-ink' },
  { to: '/students', icon: Users, label: 'Students', desc: 'Manage student profiles and progress', color: 'bg-sky/20 text-ink' },
  { to: '/planning-notes', icon: StickyNote, label: 'Planning Notes', desc: 'Your workspace for lesson notes', color: 'bg-leaf/10 text-leaf-dark' },
];

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const displayName = user && 'full_name' in user && user.full_name ? user.full_name.split(' ')[0] : 'Educator';
  const institution = user && 'institution_name' in user ? (user as { institution_name?: string }).institution_name : undefined;
  const schoolName = user && 'school_name' in user ? user.school_name : undefined;
  const [showSetupBanner, setShowSetupBanner] = useState(false);

  useEffect(() => {
    if (!institution && !schoolName) {
      setShowSetupBanner(true);
    }
  }, [institution, schoolName]);

  const checkSchool = async () => {
    try {
      const info = await schools.mine();
      setShowSetupBanner(!info);
    } catch {
      setShowSetupBanner(true);
    }
  };

  useEffect(() => {
    if (isAdmin) checkSchool();
  }, [isAdmin]);

  return (
    <div className="animate-fade-in">
      {showSetupBanner && (
        <div className="mb-6 p-4 bg-sky/15 border border-sky/30 rounded-2xl flex items-start gap-3">
          <Building2 size={20} className="text-ink mt-0.5 shrink-0" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-ink mb-1">Complete your institution setup</h4>
            <p className="text-sm text-eco-text/60">
              {isAdmin
                ? 'Set up your school details and invite educators to join your team.'
                : 'Add your institution details in Settings, or join a school with an invite code to connect with your team.'}
            </p>
            <div className="flex gap-2 mt-2">
              <Link to="/settings" className="text-xs font-medium text-eco-accent hover:text-eco-hover transition-colors">
                Go to Settings →
              </Link>
              <Link to="/school-setup" className="text-xs font-medium text-eco-accent hover:text-eco-hover transition-colors ml-4">
                Set up a school →
              </Link>
              {!isAdmin && (
                <Link to="/join-school" className="text-xs font-medium text-eco-accent hover:text-eco-hover transition-colors ml-4">
                  Join a school →
                </Link>
              )}
            </div>
          </div>
          <button onClick={() => setShowSetupBanner(false)} className="text-eco-text/30 hover:text-ink transition-colors">
            <AlertCircle size={16} />
          </button>
        </div>
      )}

      <div className="mb-8">
        <h2 className="text-3xl font-serif text-ink">Welcome back, {displayName}</h2>
        <p className="text-eco-text/60 mt-2">
          {schoolName ? `${schoolName} · ` : ''}What would you like to work on today?
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {toolsList.map(tool => (
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

        {isAdmin && (
          <Link
            to="/school-admin"
            className="group bg-eco-card rounded-2xl border border-eco-border p-5 hover:border-leaf/40 hover:shadow-sm transition-all duration-200"
          >
            <div className="w-10 h-10 rounded-xl bg-clay/20 text-ink flex items-center justify-center mb-3">
              <Building2 size={20} />
            </div>
            <h3 className="font-sans text-base font-semibold text-ink mb-1">School Admin</h3>
            <p className="text-sm text-eco-text/60 leading-relaxed">Manage educators, lookup users, school settings</p>
            <div className="mt-3 flex items-center gap-1 text-xs font-medium text-eco-accent group-hover:text-eco-hover transition-colors">
              Open <ArrowRight size={12} />
            </div>
          </Link>
        )}
      </div>
    </div>
  );
}
