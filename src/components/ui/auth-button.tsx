import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useAuth } from "../../../supabase/auth";
import { useState } from "react";

interface AuthButtonProps {
  action: "login" | "signup" | "logout";
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  children?: React.ReactNode;
  className?: string;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
}

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

  const handleClick = async () => {
    setLoading(true);
    try {
      if (action === "logout") {
        await signOut();
        onSuccess?.();
      }
      // For login and signup, the actual auth calls are handled by the forms
      // This component just provides the UI wrapper
    } catch (error) {
      const err = error instanceof Error ? error : new Error("Authentication failed");
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
