import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import JoinSchool from './pages/JoinSchool';
import SchoolSetup from './pages/SchoolSetup';
import Contact from './pages/Contact';
import Privacy from './pages/Privacy';
import Dashboard from './pages/Dashboard';
import LessonPlanning from './pages/LessonPlanning';
import Companion from './pages/Companion';
import GreatStories from './pages/GreatStories';
import Imaginarium from './pages/Imaginarium';
import PdExpert from './pages/PdExpert';
import Students from './pages/Students';
import PlanningNotes from './pages/PlanningNotes';
import StudentLearning from './pages/StudentLearning';
import SchoolAdmin from './pages/SchoolAdmin';
import Settings from './pages/Settings';

function RootRedirect() {
  const { user, loading, isStudent } = useAuth();
  const params = new URLSearchParams(window.location.search);
  const resetToken = params.get('reset_token');
  if (resetToken) {
    return <Navigate to={`/reset-password?token=${encodeURIComponent(resetToken)}`} replace />;
  }
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={isStudent ? '/learn' : '/dashboard'} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<ErrorBoundary><Login /></ErrorBoundary>} />
          <Route path="/signup" element={<ErrorBoundary><Signup /></ErrorBoundary>} />
          <Route path="/forgot-password" element={<ErrorBoundary><ForgotPassword /></ErrorBoundary>} />
          <Route path="/reset-password" element={<ErrorBoundary><ResetPassword /></ErrorBoundary>} />
          <Route path="/join-school" element={<ErrorBoundary><JoinSchool /></ErrorBoundary>} />
          <Route path="/school-setup" element={<ErrorBoundary><SchoolSetup /></ErrorBoundary>} />
          <Route path="/contact" element={<ErrorBoundary><Contact /></ErrorBoundary>} />
          <Route path="/privacy" element={<ErrorBoundary><Privacy /></ErrorBoundary>} />

          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<ProtectedRoute requireRole="educator"><Dashboard /></ProtectedRoute>} />
            <Route path="/lesson-planning" element={<ProtectedRoute requireRole="educator"><LessonPlanning /></ProtectedRoute>} />
            <Route path="/companion" element={<ProtectedRoute requireRole="educator"><Companion /></ProtectedRoute>} />
            <Route path="/great-stories" element={<ProtectedRoute requireRole="educator"><GreatStories /></ProtectedRoute>} />
            <Route path="/imaginarium" element={<ProtectedRoute requireRole="educator"><Imaginarium /></ProtectedRoute>} />
            <Route path="/pd-expert" element={<ProtectedRoute requireRole="educator"><PdExpert /></ProtectedRoute>} />
            <Route path="/students" element={<ProtectedRoute requireRole="educator"><Students /></ProtectedRoute>} />
            <Route path="/planning-notes" element={<ProtectedRoute requireRole="educator"><PlanningNotes /></ProtectedRoute>} />
            <Route path="/school-admin" element={<ProtectedRoute requireRole="admin"><SchoolAdmin /></ProtectedRoute>} />
            <Route path="/learn" element={<ProtectedRoute requireRole="student"><StudentLearning /></ProtectedRoute>} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
