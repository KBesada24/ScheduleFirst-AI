/**
 * Notification System Usage Examples
 * 
 * This file demonstrates how to use the notification system
 * implemented for task 12.3
 * 
 * Requirements:
 * - Success messages display for 3 seconds (Requirement 11.5)
 * - Error messages display until dismissed (Requirement 11.4)
 * - Notifications positioned in top-right corner
 */

import { useToast } from "@/components/ui/use-toast";
import { 
  createSuccessToast, 
  createErrorToast, 
  createInfoToast,
  createWarningToast,
  notifications 
} from "@/lib/notifications";

// Example 1: Using predefined notification presets
function ExampleWithPresets() {
  const { toast } = useToast();

  const handleLogin = async () => {
    try {
      // ... login logic
      toast(notifications.loginSuccess); // Auto-dismisses after 3 seconds
    } catch (error) {
      toast(notifications.loginError); // Stays until dismissed
    }
  };

  const handleScheduleUpdate = async () => {
    try {
      // ... schedule update logic
      toast(notifications.scheduleSaved); // Auto-dismisses after 3 seconds
    } catch (error) {
      toast(notifications.scheduleError); // Stays until dismissed
    }
  };

  return null;
}

// Example 2: Creating custom notifications
function ExampleWithCustomNotifications() {
  const { toast } = useToast();

  const handleCustomSuccess = () => {
    // Success notification - auto-dismisses after 3 seconds
    toast(createSuccessToast("Operation completed!", {
      description: "Your changes have been saved successfully."
    }));
  };

  const handleCustomError = () => {
    // Error notification - stays until manually dismissed
    toast(createErrorToast("Operation failed", {
      description: "Please try again or contact support."
    }));
  };

  const handleCustomInfo = () => {
    // Info notification - auto-dismisses after 3 seconds
    toast(createInfoToast("Did you know?", {
      description: "You can use keyboard shortcuts to navigate faster."
    }));
  };

  const handleCustomWarning = () => {
    // Warning notification - auto-dismisses after 4 seconds
    toast(createWarningToast("Warning", {
      description: "This action may affect your schedule."
    }));
  };

  return null;
}

// Example 3: Custom duration
function ExampleWithCustomDuration() {
  const { toast } = useToast();

  const handleCustomDuration = () => {
    // Override default duration (3 seconds for success)
    toast(createSuccessToast("Quick message", {
      duration: 1500 // 1.5 seconds
    }));
  };

  const handlePersistentSuccess = () => {
    // Make success message stay until dismissed
    toast(createSuccessToast("Important success", {
      duration: Infinity // Stays until dismissed
    }));
  };

  return null;
}

// Example 4: Dismissing notifications programmatically
function ExampleWithDismiss() {
  const { toast, dismiss } = useToast();

  const handleWithDismiss = () => {
    const { id } = toast(createSuccessToast("Processing..."));
    
    // Later, dismiss this specific toast
    setTimeout(() => {
      dismiss(id);
    }, 2000);
  };

  const handleDismissAll = () => {
    // Dismiss all toasts
    dismiss();
  };

  return null;
}

export {};
