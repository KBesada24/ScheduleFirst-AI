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

interface LoginFormValues {
  email: string;
  password: string;
}

export default function LoginForm() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const {
    values,
    errors,
    isSubmitting,
    setValue,
    handleSubmit,
  } = useFormSubmission<LoginFormValues>(
    { email: "", password: "" },
    {
      validationRules: {
        email: combine(required, email),
        password: combine(required, minLength(6)),
      },
      onSubmit: async (formValues) => {
        await signIn(formValues.email, formValues.password);
        
        // Success notification - auto-dismisses after 3 seconds (Requirement 11.5)
        toast(notifications.loginSuccess);
        
        // Check for stored redirect URL
        const redirectUrl = sessionStorage.getItem("redirectAfterLogin");
        if (redirectUrl) {
          sessionStorage.removeItem("redirectAfterLogin");
          navigate(redirectUrl);
        } else {
          navigate("/dashboard");
        }
      },
      onError: (err) => {
        console.error("Login error:", err);
        
        // Error notification - stays until dismissed (Requirement 11.4)
        toast(notifications.loginError);
      },
    }
  );

  return (
    <AuthLayout>
      <div className="bg-white rounded-2xl shadow-sm p-8 w-full max-w-md mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
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
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-sm font-medium text-gray-700">Password</Label>
              <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:text-blue-500">
                Forgot password?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={values.password}
              onChange={(e) => setValue("password", e.target.value)}
              required
              className={`h-12 rounded-lg border-gray-300 focus:ring-blue-500 focus:border-blue-500 ${errors.password ? "border-red-500" : ""}`}
            />
            {errors.password && <p className="text-sm text-red-500">{errors.password}</p>}
          </div>
          <AuthButton 
            action="login"
            disabled={isSubmitting}
            className="w-full h-12 rounded-full bg-black text-white hover:bg-gray-800 text-sm font-medium"
          >
            Sign in
          </AuthButton>
      
      
          <div className="text-sm text-center text-gray-600 mt-6">
            Don't have an account?{" "}
            <Link to="/signup" className="text-blue-600 hover:underline font-medium">
              Sign up
            </Link>
          </div>
        </form>
      </div>
    </AuthLayout>
  );
}
