import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';

const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const JoinSchool = lazy(() => import('./pages/JoinSchool'));
const SchoolSetup = lazy(() => import('./pages/SchoolSetup'));
const Contact = lazy(() => import('./pages/Contact'));
const Privacy = lazy(() => import('./pages/Privacy'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const LessonPlanning = lazy(() => import('./pages/LessonPlanning'));
const Companion = lazy(() => import('./pages/Companion'));
const GreatStories = lazy(() => import('./pages/GreatStories'));
const Imaginarium = lazy(() => import('./pages/Imaginarium'));
const PdExpert = lazy(() => import('./pages/PdExpert'));
const Students = lazy(() => import('./pages/Students'));
const PlanningNotes = lazy(() => import('./pages/PlanningNotes'));
const StudentLearning = lazy(() => import('./pages/StudentLearning'));
const SchoolAdmin = lazy(() => import('./pages/SchoolAdmin'));
const Settings = lazy(() => import('./pages/Settings'));

function RouteFallback() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="animate-spin text-leaf" size={28} />
    </div>
  );
}

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
        <Suspense fallback={<RouteFallback />}>
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
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
