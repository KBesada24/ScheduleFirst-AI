import { useAuth } from "../../../supabase/auth";
import { AuthButton } from "@/components/ui/auth-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useNavigate, Link } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { useToast } from "@/components/ui/use-toast";
import { notifications } from "@/lib/notifications";
import { useFormSubmission } from "@/hooks/useFormSubmission";
import { required, email, minLength, combine } from "@/lib/form-validation";

interface SignUpFormValues {
  fullName: string;
  email: string;
  password: string;
}

export default function SignUpForm() {
  const { signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleGoogleSignIn = async () => {
    try {
      await signInWithGoogle();
      // Note: User will be redirected to Google, then back to the app
      // The redirect is handled by Supabase OAuth config
    } catch (err) {
      console.error("Google sign in error:", err);
      toast({
        title: "Sign up failed",
        description: "Could not sign up with Google. Please try again.",
        variant: "destructive",
      });
    }
  };

  const {
    values,
    errors,
    isSubmitting,
    setValue,
    handleSubmit,
  } = useFormSubmission<SignUpFormValues>(
    { fullName: "", email: "", password: "" },
    {
      validationRules: {
        fullName: combine(required, minLength(2)),
        email: combine(required, email),
        password: combine(required, minLength(8)),
      },
      onSubmit: async (formValues) => {
        await signUp(formValues.email, formValues.password, formValues.fullName);

        // Success notification - auto-dismisses after 3 seconds (Requirement 11.5)
        toast(notifications.signupSuccess);

        navigate("/success");
      },
      onError: (err) => {
        console.error("Signup error:", err);

        // Error notification - stays until dismissed (Requirement 11.4)
        toast(notifications.signupError);
      },
    }
  );

  return (
    <AuthLayout>
      <div className="bg-white rounded-2xl shadow-sm p-8 w-full max-w-md mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="fullName" className="text-sm font-medium text-gray-700">Full Name</Label>
            <Input
              id="fullName"
              placeholder="John Doe"
              value={values.fullName}
              onChange={(e) => setValue("fullName", e.target.value)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${errors.fullName ? "border-red-500" : ""}`}
            />
            {errors.fullName && <p className="text-sm text-red-500">{errors.fullName}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium text-gray-700">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={values.email}
              onChange={(e) => setValue("email", e.target.value)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${errors.email ? "border-red-500" : ""}`}
            />
            {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium text-gray-700">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Create a password"
              value={values.password}
              onChange={(e) => setValue("password", e.target.value)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${errors.password ? "border-red-500" : ""}`}
            />
            {errors.password && <p className="text-sm text-red-500">{errors.password}</p>}
            {!errors.password && <p className="text-xs text-gray-500 mt-1">Password must be at least 8 characters</p>}
          </div>

          <AuthButton
            action="signup"
            disabled={isSubmitting}
            className="w-full h-12 rounded-full bg-black text-white hover:bg-gray-800 text-sm font-medium"
          >
            Create account
          </AuthButton>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Or continue with</span>
            </div>
          </div>

          {/* Google Sign-up Button */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            className="w-full h-12 rounded-full border-2 border-gray-300 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400 text-sm font-medium flex items-center justify-center gap-3 transition-all"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continue with Google
          </button>


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