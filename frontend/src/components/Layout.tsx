import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Home, BookOpen, Users, MessageCircle, Sparkles, GraduationCap,
  StickyNote, Settings, LogOut, Menu, X, BookMarked, Lightbulb, ChevronDown, Building2
} from 'lucide-react';

const educatorNav = [
  { to: '/dashboard', icon: Home, label: 'Home' },
  { to: '/lesson-planning', icon: BookOpen, label: 'Lesson Planning' },
  { to: '/companion', icon: MessageCircle, label: 'Companion' },
  { to: '/great-stories', icon: BookMarked, label: 'Great Stories' },
  { to: '/imaginarium', icon: Sparkles, label: 'Imaginarium' },
  { to: '/pd-expert', icon: GraduationCap, label: 'PD Expert' },
  { to: '/students', icon: Users, label: 'Students' },
  { to: '/planning-notes', icon: StickyNote, label: 'Planning Notes' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

const adminNav = { to: '/school-admin', icon: Building2, label: 'School Admin' };

const studentNav = [
  { to: '/learn', icon: Lightbulb, label: 'Learn' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
  const { user, logout, isStudent, isAdmin } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const navigate = useNavigate();
  const baseNav = isStudent ? studentNav : educatorNav;
  const navItems = !isStudent && isAdmin
    ? [...baseNav.slice(0, -1), adminNav, baseNav[baseNav.length - 1]]
    : baseNav;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const displayName = user && 'name' in user ? user.name : 'User';

  return (
    <div className="flex h-screen bg-eco-bg">
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-eco-card border-r border-eco-border
        transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:z-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          <div className="p-5 border-b border-eco-border">
            <h1 className="text-2xl font-serif text-ink tracking-tight">Guide</h1>
            <p className="text-xs text-eco-text/60 mt-0.5">Montessori Learning Platform</p>
          </div>

          <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
                  transition-colors duration-150
                  ${isActive
                    ? 'bg-leaf/15 text-leaf-dark'
                    : 'text-eco-text/70 hover:bg-sand/50 hover:text-ink'}
                `}
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="p-3 border-t border-eco-border">
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm hover:bg-sand/50 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-leaf/20 flex items-center justify-center text-leaf-dark font-semibold text-xs">
                  {displayName.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 text-left min-w-0">
                  <div className="truncate font-medium text-ink">{displayName}</div>
                  <div className="truncate text-xs text-eco-text/60">
                    {'email' in (user || {}) ? (user as { email: string }).email : ''}
                  </div>
                </div>
                <ChevronDown size={14} className={`text-eco-text/40 transition-transform ${profileOpen ? 'rotate-180' : ''}`} />
              </button>
              {profileOpen && (
                <div className="absolute bottom-full left-0 right-0 mb-1 bg-eco-card border border-eco-border rounded-xl shadow-lg overflow-hidden animate-fade-in">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-danger hover:bg-soft-rose/30 transition-colors"
                  >
                    <LogOut size={16} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/20 z-30 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center gap-3 px-4 py-3 bg-eco-card border-b border-eco-border">
          <button onClick={() => setSidebarOpen(true)} className="p-1.5 rounded-lg hover:bg-sand/50" aria-label="Open menu">
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <h1 className="text-lg font-serif text-ink">Guide</h1>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
