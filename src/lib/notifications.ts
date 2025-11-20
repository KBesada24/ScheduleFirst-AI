/**
 * Notification Utilities
 * 
 * Centralized notification system for success/error messages
 * Uses shadcn/ui toast component
 * 
 * Requirements:
 * - Success messages display for 3 seconds (11.5)
 * - Error messages display until dismissed (11.4)
 * - Notifications positioned in top-right corner
 */

// Note: This module provides a wrapper around the toast hook
// Import and use the toast hook from @/components/ui/use-toast in components

export interface NotificationOptions {
  duration?: number;
  description?: string;
}

/**
 * Create a success toast configuration
 * Success messages auto-dismiss after 3 seconds (Requirement 11.5)
 */
export function createSuccessToast(
  title: string,
  options: NotificationOptions = {}
) {
  return {
    title,
    description: options.description,
    variant: "success" as const,
    duration: options.duration !== undefined ? options.duration : 3000,
  };
}

/**
 * Create an error toast configuration
 * Error messages stay until manually dismissed (Requirement 11.4)
 */
export function createErrorToast(
  title: string,
  options: NotificationOptions = {}
) {
  return {
    title,
    description: options.description,
    variant: "destructive" as const,
    duration: options.duration !== undefined ? options.duration : Infinity,
  };
}

/**
 * Create an info toast configuration
 */
export function createInfoToast(
  title: string,
  options: NotificationOptions = {}
) {
  return {
    title,
    description: options.description,
    duration: options.duration !== undefined ? options.duration : 3000,
  };
}

/**
 * Create a warning toast configuration
 */
export function createWarningToast(
  title: string,
  options: NotificationOptions = {}
) {
  return {
    title,
    description: options.description,
    variant: "destructive" as const,
    duration: options.duration !== undefined ? options.duration : 4000,
  };
}

/**
 * Notification presets for common actions
 * Use with the toast hook: toast(notifications.loginSuccess)
 * 
 * Success notifications auto-dismiss after 3 seconds
 * Error notifications stay until manually dismissed
 */
export const notifications = {
  // Auth
  loginSuccess: createSuccessToast("Successfully logged in!"),
  loginError: createErrorToast("Failed to log in", { description: "Please check your credentials." }),
  logoutSuccess: createSuccessToast("Successfully logged out!"),
  signupSuccess: createSuccessToast("Account created successfully!"),
  signupError: createErrorToast("Failed to create account", { description: "Please try again." }),
  
  // Schedule
  sectionAdded: createSuccessToast("Section added to your schedule!"),
  sectionRemoved: createSuccessToast("Section removed from your schedule!"),
  scheduleConflict: createErrorToast("Schedule conflict detected!"),
  scheduleSaved: createSuccessToast("Schedule saved successfully!"),
  scheduleError: createErrorToast("Failed to update schedule", { description: "Please try again." }),
  
  // Search
  searchError: createErrorToast("Search failed", { description: "Please try again." }),
  noResults: createInfoToast("No results found", { description: "Try adjusting your search." }),
  
  // Network
  networkError: createErrorToast("Network error", { description: "Please check your connection." }),
  serverError: createErrorToast("Server error", { description: "Please try again later." }),
  
  // Generic
  saveSuccess: createSuccessToast("Changes saved successfully!"),
  saveError: createErrorToast("Failed to save changes", { description: "Please try again." }),
  deleteSuccess: createSuccessToast("Deleted successfully!"),
  deleteError: createErrorToast("Failed to delete", { description: "Please try again." }),
  copySuccess: createSuccessToast("Copied to clipboard!"),
};
