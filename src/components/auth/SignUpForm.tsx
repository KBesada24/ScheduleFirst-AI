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
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

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