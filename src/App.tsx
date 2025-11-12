import { Routes, Route, Navigate } from "react-router-dom";
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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
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