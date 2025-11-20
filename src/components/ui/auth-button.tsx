import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useAuth } from "../../../supabase/auth";
import { useState } from "react";
import { useToast } from "@/components/ui/use-toast";
import { notifications } from "@/lib/notifications";

/**
 * Props for the AuthButton component
 */
interface AuthButtonProps {
  /** The authentication action to perform */
  action: "login" | "signup" | "logout";
  /** Callback function called on successful authentication */
  onSuccess?: () => void;
  /** Callback function called on authentication error */
  onError?: (error: Error) => void;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Button content (text or elements) */
  children?: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Button visual variant */
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
}

/**
 * AuthButton - A button component for authentication actions
 * 
 * Features:
 * - Handles login, signup, and logout actions
 * - Shows loading state during authentication
 * - Displays success/error notifications
 * - Integrates with useAuth hook
 * - Supports custom callbacks for success/error
 * 
 * @example
 * ```tsx
 * <AuthButton action="login" onSuccess={() => navigate('/dashboard')}>
 *   Sign In
 * </AuthButton>
 * ```
 * 
 * @param action - The authentication action to perform (login, signup, logout)
 * @param onSuccess - Optional callback called on successful authentication
 * @param onError - Optional callback called on authentication error
 * @param disabled - Whether the button is disabled
 * @param children - Button content
 * @param className - Additional CSS classes
 * @param variant - Button visual variant
 */
export function AuthButton({
  action,
  onSuccess,
  onError,
  disabled = false,
  children,
  className,
  variant = "default",
}: AuthButtonProps) {
  const { signIn, signUp, signOut } = useAuth();
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleClick = async () => {
    setLoading(true);
    try {
      if (action === "logout") {
        await signOut();
        // Success notification - auto-dismisses after 3 seconds (Requirement 11.5)
        toast(notifications.logoutSuccess);
        onSuccess?.();
      }
      // For login and signup, the actual auth calls are handled by the forms
      // This component just provides the UI wrapper
    } catch (error) {
      const err = error instanceof Error ? error : new Error("Authentication failed");
      // Error notification - stays until dismissed (Requirement 11.4)
      toast(notifications.loginError);
      onError?.(err);
    } finally {
      setLoading(false);
    }
  };

  const getButtonText = () => {
    if (loading) {
      switch (action) {
        case "login":
          return "Signing in...";
        case "signup":
          return "Creating account...";
        case "logout":
          return "Signing out...";
      }
    }
    return children || (action === "login" ? "Sign in" : action === "signup" ? "Sign up" : "Log out");
  };

  return (
    <Button
      type={action === "logout" ? "button" : "submit"}
      onClick={action === "logout" ? handleClick : undefined}
      disabled={disabled || loading}
      className={className}
      variant={variant}
    >
      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {getButtonText()}
    </Button>
  );
}
