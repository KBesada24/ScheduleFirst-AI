import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

interface RefreshButtonProps {
  onRefresh: () => void | Promise<void>;
  disabled?: boolean;
  cooldownSeconds?: number;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
}

export function RefreshButton({
  onRefresh,
  disabled = false,
  cooldownSeconds = 2,
  variant = "outline",
  size = "default",
  className = "",
}: RefreshButtonProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);

  useEffect(() => {
    if (cooldownRemaining > 0) {
      const timer = setTimeout(() => {
        setCooldownRemaining(cooldownRemaining - 1);
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [cooldownRemaining]);

  const handleRefresh = async () => {
    if (isRefreshing || cooldownRemaining > 0) {
      return;
    }

    setIsRefreshing(true);

    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
      setCooldownRemaining(cooldownSeconds);
    }
  };

  const isDisabled = disabled || isRefreshing || cooldownRemaining > 0;

  return (
    <Button
      onClick={handleRefresh}
      disabled={isDisabled}
      variant={variant}
      size={size}
      className={className}
    >
      <RefreshCw 
        className={`h-4 w-4 ${size !== "icon" ? "mr-2" : ""} ${isRefreshing ? "animate-spin" : ""}`}
      />
      {size !== "icon" && (
        <>
          {cooldownRemaining > 0 
            ? `Wait ${cooldownRemaining}s` 
            : isRefreshing 
            ? "Refreshing..." 
            : "Refresh"}
        </>
      )}
    </Button>
  );
}
