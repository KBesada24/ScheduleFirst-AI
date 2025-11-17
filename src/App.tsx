import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import LandingPage from "./components/pages/home";
import Dashboard from "./components/pages/dashboard";
import ScheduleBuilder from "./components/pages/schedule-builder";
import AdminPage from "./components/pages/admin";
import SuccessPage from "./components/pages/success";
// Add these imports
import AuthLayout from "./components/auth/AuthLayout";
import LoginForm from "./components/auth/LoginForm";
import SignUpForm from "./components/auth/SignUpForm";
import { useAuth } from "../supabase/auth";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";

/**
 * ProtectedRoute - Wrapper component for routes that require authentication
 * 
 * Features:
 * - Checks user authentication status
 * - Shows loading spinner during auth verification
 * - Redirects unauthenticated users to login
 * - Preserves intended destination for post-login redirect
 * - Handles return URL in session storage
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  
  useEffect(() => {
    // Store intended destination if user is not authenticated
    if (!loading && !user) {
      sessionStorage.setItem("redirectAfterLogin", location.pathname + location.search);
    }
  }, [loading, user, location]);
  
  // Show loading spinner during authentication check
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Verifying authentication...</p>
        </div>
      </div>
    );
  }
  
  // Redirect to login if not authenticated
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      {/* Auth routes - LoginForm and SignUpForm already include AuthLayout */}
      <Route path="/login" element={<LoginForm />} />
      <Route path="/signup" element={<SignUpForm />} />
      
      {/* Protected routes */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/schedule-builder" element={<ProtectedRoute><ScheduleBuilder /></ProtectedRoute>} />
      <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
      <Route path="/success" element={<ProtectedRoute><SuccessPage /></ProtectedRoute>} />
    </Routes>
  );
}

export default function App() {
  return <AppRoutes />;
}