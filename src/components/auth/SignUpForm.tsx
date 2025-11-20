import { useState } from "react";
import { useAuth } from "../../../supabase/auth";
import { AuthButton } from "@/components/ui/auth-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useNavigate, Link } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { useToast } from "@/components/ui/use-toast";

export default function SignUpForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [fullNameError, setFullNameError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const validateFullName = (name: string): boolean => {
    setFullNameError("");
    if (!name || name.trim().length === 0) {
      setFullNameError("Full name is required");
      return false;
    }
    if (name.trim().length < 2) {
      setFullNameError("Full name must be at least 2 characters");
      return false;
    }
    return true;
  };

  const validateEmail = (email: string): boolean => {
    setEmailError("");
    if (!email) {
      setEmailError("Email is required");
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setEmailError("Please enter a valid email address");
      return false;
    }
    return true;
  };

  const validatePassword = (password: string): boolean => {
    setPasswordError("");
    if (!password) {
      setPasswordError("Password is required");
      return false;
    }
    if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setFullNameError("");
    setEmailError("");
    setPasswordError("");
    
    // Validate all fields
    const isFullNameValid = validateFullName(fullName);
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);
    
    if (!isFullNameValid || !isEmailValid || !isPasswordValid) {
      return;
    }
    
    setSubmitting(true);
    try {
      await signUp(email, password, fullName);
      toast({
        title: "Account created successfully!",
        description: "Welcome to ScheduleFirst AI. Let's build your schedule.",
        duration: 5000,
      });
      navigate("/success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error creating account";
      setError(msg);
      toast({ title: "Sign up failed", description: msg, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout>
      <div className="bg-white rounded-2xl shadow-sm p-8 w-full max-w-md mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="fullName" className="text-sm font-medium text-gray-700">Full Name</Label>
            <Input
              id="fullName"
              placeholder="John Doe"
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                setFullNameError("");
              }}
              onBlur={() => validateFullName(fullName)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${fullNameError ? "border-red-500" : ""}`}
            />
            {fullNameError && <p className="text-sm text-red-500">{fullNameError}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium text-gray-700">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setEmailError("");
              }}
              onBlur={() => validateEmail(email)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${emailError ? "border-red-500" : ""}`}
            />
            {emailError && <p className="text-sm text-red-500">{emailError}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium text-gray-700">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Create a password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setPasswordError("");
              }}
              onBlur={() => validatePassword(password)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${passwordError ? "border-red-500" : ""}`}
            />
            {passwordError && <p className="text-sm text-red-500">{passwordError}</p>}
            {!passwordError && <p className="text-xs text-gray-500 mt-1">Password must be at least 8 characters</p>}
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          
          <AuthButton 
            action="signup"
            disabled={submitting}
            className="w-full h-12 rounded-full bg-black text-white hover:bg-gray-800 text-sm font-medium"
          >
            Create account
          </AuthButton>
          
          
          <div className="text-xs text-center text-gray-500 mt-6">
            By creating an account, you agree to our{" "}
            <Link to="/" className="text-blue-600 hover:underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link to="/" className="text-blue-600 hover:underline">
              Privacy Policy
            </Link>
          </div>
          
          <div className="text-sm text-center text-gray-600 mt-6">
            Already have an account?{" "}
            <Link to="/login" className="text-blue-600 hover:underline font-medium">
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </AuthLayout>
  );
}