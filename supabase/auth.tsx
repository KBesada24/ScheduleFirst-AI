import { createContext, useContext, useEffect, useState } from "react";
import { User } from "@supabase/supabase-js";
import { supabase } from "./supabase";

type AuthContextType = {
  user: User | null;
  loading: boolean;
  error: Error | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Check active sessions and sets the user
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for changes on auth state (signed in, signed out, etc.)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Retry helper with exponential backoff
  const retryWithBackoff = async <T,>(
    fn: () => Promise<T>,
    maxRetries = 3
  ): Promise<T> => {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await fn();
      } catch (err) {
        lastError = err instanceof Error ? err : new Error("Unknown error");

        // Check if it's a network error that should be retried
        const isNetworkError =
          lastError.message.includes("network") ||
          lastError.message.includes("fetch") ||
          lastError.message.includes("Failed to fetch");

        if (!isNetworkError || attempt === maxRetries - 1) {
          throw lastError;
        }

        // Exponential backoff: 1s, 2s, 4s
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError || new Error("Max retries exceeded");
  };

  const signUp = async (email: string, password: string, fullName: string) => {
    setError(null);
    try {
      await retryWithBackoff(async () => {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
            },
          },
        });
        if (error) {
          // Provide clear error messages
          if (error.message.includes("already registered")) {
            throw new Error("This email is already registered. Please sign in instead.");
          } else if (error.message.includes("password")) {
            throw new Error("Password must be at least 6 characters long.");
          } else if (error.message.includes("email")) {
            throw new Error("Please provide a valid email address.");
          }
          throw error;
        }
      });
    } catch (err) {
      const authError = err instanceof Error ? err : new Error("Sign up failed");
      setError(authError);
      throw authError;
    }
  };

  const signIn = async (email: string, password: string) => {
    setError(null);
    try {
      await retryWithBackoff(async () => {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) {
          // Provide clear error messages
          if (error.message.includes("Invalid login credentials")) {
            throw new Error("Invalid email or password. Please try again.");
          } else if (error.message.includes("Email not confirmed")) {
            throw new Error("Please verify your email address before signing in.");
          } else if (error.message.includes("network") || error.message.includes("fetch")) {
            throw new Error("Network error. Please check your connection and try again.");
          }
          throw error;
        }
      });
    } catch (err) {
      const authError = err instanceof Error ? err : new Error("Sign in failed");
      setError(authError);
      console.error("Supabase auth error:", authError);
      throw authError;
    }
  };

  const signInWithGoogle = async () => {
    setError(null);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/schedule-builder`,
        },
      });
      if (error) throw error;
    } catch (err) {
      const authError = err instanceof Error ? err : new Error("Google sign in failed");
      setError(authError);
      throw authError;
    }
  };

  const signOut = async () => {
    setError(null);
    try {
      await retryWithBackoff(async () => {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;
      });
      // Clear any stored session data
      localStorage.removeItem("supabase.auth.token");
    } catch (err) {
      const authError = err instanceof Error ? err : new Error("Sign out failed");
      setError(authError);
      throw authError;
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, signIn, signUp, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
