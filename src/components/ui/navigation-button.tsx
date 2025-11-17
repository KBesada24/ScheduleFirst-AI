import { Link, useNavigate } from "react-router-dom";
import { Button, ButtonProps } from "@/components/ui/button";
import { useAuth } from "../../../supabase/auth";
import { Loader2 } from "lucide-react";
import { useState } from "react";

export interface NavigationButtonProps extends Omit<ButtonProps, "onClick"> {
  to: string;
  children: React.ReactNode;
  requiresAuth?: boolean;
  onClick?: () => void | Promise<void>;
  external?: boolean;
}

/**
 * NavigationButton - A reusable button component that handles navigation
 * 
 * Features:
 * - Integrates with React Router for client-side navigation
 * - Checks authentication for protected routes
 * - Shows loading state during navigation
 * - Supports external links
 * - Provides hover and active state styling
 * 
 * @param to - Target route or URL
 * @param children - Button content
 * @param requiresAuth - Whether the route requires authentication
 * @param onClick - Optional callback before navigation
 * @param external - Whether the link is external (opens in new tab)
 * @param ...props - Additional Button props (variant, size, etc.)
 */
export function NavigationButton({
  to,
  children,
  requiresAuth = false,
  onClick,
  external = false,
  disabled,
  ...props
}: NavigationButtonProps) {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [isNavigating, setIsNavigating] = useState(false);

  const handleClick = async (e: React.MouseEvent) => {
    // Prevent default link behavior
    e.preventDefault();

    // If button is disabled or already navigating, do nothing
    if (disabled || isNavigating) return;

    // Check authentication if required
    if (requiresAuth && !user) {
      // Store intended destination for post-login redirect
      sessionStorage.setItem("redirectAfterLogin", to);
      navigate("/login");
      return;
    }

    try {
      setIsNavigating(true);

      // Execute optional onClick callback
      if (onClick) {
        await onClick();
      }

      // Navigate to destination
      if (external) {
        window.open(to, "_blank", "noopener,noreferrer");
      } else {
        navigate(to);
      }
    } catch (error) {
      console.error("Navigation error:", error);
    } finally {
      setIsNavigating(false);
    }
  };

  // Show loading state if checking auth
  if (authLoading && requiresAuth) {
    return (
      <Button disabled {...props}>
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        Loading...
      </Button>
    );
  }

  // For external links, use anchor tag
  if (external) {
    return (
      <Button
        asChild
        disabled={disabled || isNavigating}
        {...props}
      >
        <a
          href={to}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleClick}
        >
          {isNavigating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Loading...
            </>
          ) : (
            children
          )}
        </a>
      </Button>
    );
  }

  // For internal navigation, use Link
  return (
    <Button
      asChild
      disabled={disabled || isNavigating}
      {...props}
    >
      <Link to={to} onClick={handleClick}>
        {isNavigating ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            Loading...
          </>
        ) : (
          children
        )}
      </Link>
    </Button>
  );
}
