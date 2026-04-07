import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  requireRole?: 'educator' | 'student' | 'admin';
}

export default function ProtectedRoute({ children, requireRole }: Props) {
  const { user, loading, isEducator, isStudent, isAdmin } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-paper">
        <Loader2 className="animate-spin-slow text-leaf" size={32} />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (requireRole === 'educator' && !isEducator) return <Navigate to="/learn" replace />;
  if (requireRole === 'student' && !isStudent) return <Navigate to="/dashboard" replace />;
  if (requireRole === 'admin' && !isAdmin) return <Navigate to="/dashboard" replace />;

  return <>{children}</>;
}
