import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Database, Trash2, Loader2, AlertTriangle } from "lucide-react";
import { seedDatabase, clearDatabase } from "@/lib/api-endpoints";
import { useToast } from "@/components/ui/use-toast";
import { createSuccessToast, createErrorToast } from "@/lib/notifications";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface AdminActionButtonProps {
  action: "seed" | "clear";
  onSuccess: (message: string) => void;
  onError: (error: Error) => void;
  requireConfirmation?: boolean;
  disabled?: boolean;
  className?: string;
}

export function AdminActionButton({
  action,
  onSuccess,
  onError,
  requireConfirmation = true,
  disabled = false,
  className = "",
}: AdminActionButtonProps) {
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const { toast } = useToast();

  const handleAction = async () => {
    setLoading(true);

    try {
      let result: any;
      let successMessage: string;

      if (action === "seed") {
        result = await seedDatabase();
        successMessage = "Database seeded successfully!";
        
        // Log seeded data details
        console.log("Database seeded:", result);
        
        // Success notification - auto-dismisses after 3 seconds (Requirement 11.5)
        toast(createSuccessToast("Database Seeded", {
          description: successMessage,
        }));
      } else {
        result = await clearDatabase();
        successMessage = "Database cleared successfully!";
        
        // Success notification - auto-dismisses after 3 seconds (Requirement 11.5)
        toast(createSuccessToast("Database Cleared", {
          description: successMessage,
        }));
      }

      onSuccess(successMessage);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(`Failed to ${action} database`);
      
      onError(err);
      
      // Error notification - stays until dismissed (Requirement 11.4)
      toast(createErrorToast("Error", {
        description: err.message || `Failed to ${action} database`,
      }));
    } finally {
      setLoading(false);
      setShowConfirmation(false);
    }
  };

  const handleClick = () => {
    if (requireConfirmation && action === "clear") {
      setShowConfirmation(true);
    } else {
      handleAction();
    }
  };

  const isDestructive = action === "clear";

  return (
    <>
      <Button
        onClick={handleClick}
        disabled={disabled || loading}
        variant={isDestructive ? "destructive" : "default"}
        className={className}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {action === "seed" ? "Seeding..." : "Clearing..."}
          </>
        ) : (
          <>
            {action === "seed" ? (
              <>
                <Database className="mr-2 h-4 w-4" />
                Seed Database
              </>
            ) : (
              <>
                <Trash2 className="mr-2 h-4 w-4" />
                Clear Database
              </>
            )}
          </>
        )}
      </Button>

      {/* Confirmation Dialog */}
      <AlertDialog open={showConfirmation} onOpenChange={setShowConfirmation}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Confirm Database Clear
            </AlertDialogTitle>
            <AlertDialogDescription>
              This action will permanently delete all data from the database.
              This cannot be undone. Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleAction}
              className="bg-red-600 hover:bg-red-700"
            >
              Yes, Clear Database
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
