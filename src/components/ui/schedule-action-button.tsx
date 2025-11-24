import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import {
  addSectionToSchedule,
  removeSectionFromSchedule,
  checkScheduleConflicts,
  TimeConflict
} from "@/lib/supabase-queries";
import { validateScheduleAction } from "@/lib/api-endpoints";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useToast } from "@/components/ui/use-toast";

interface ScheduleActionButtonProps {
  action: "add" | "remove";
  sectionId: string;
  scheduleId: string;
  currentSections?: string[];
  onSuccess?: () => void;
  onConflict?: (conflicts: TimeConflict[]) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  className?: string;
  variant?: "default" | "destructive" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
}

export function ScheduleActionButton({
  action,
  sectionId,
  scheduleId,
  currentSections = [],
  onSuccess,
  onConflict,
  onError,
  disabled = false,
  className = "",
  variant,
  size = "default",
}: ScheduleActionButtonProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleAction = async () => {
    setLoading(true);

    try {
      if (action === "add") {
        // Step 1: Validate with backend API
        const validation = await validateScheduleAction({
          scheduleId,
          sectionId,
          action: "add"
        });

        if (!validation.valid) {
          // Handle backend validation failure
          toast({
            title: "Validation Failed",
            description: validation.warnings[0] || "Cannot add section to schedule.",
            variant: "destructive",
          });
          setLoading(false);
          return;
        }

        // Step 2: Check for conflicts (Client-side + Supabase)
        const sectionsToCheck = [...currentSections, sectionId];
        const conflicts = await checkScheduleConflicts(sectionsToCheck);

        if (conflicts.length > 0) {
          // Notify about conflicts
          if (onConflict) {
            onConflict(conflicts);
          }

          toast({
            title: "Schedule Conflict Detected",
            description: `This section conflicts with ${conflicts.length} other section(s) in your schedule.`,
            variant: "destructive",
          });

          setLoading(false);
          return;
        }

        // Add section to schedule
        await addSectionToSchedule(scheduleId, sectionId);

        toast({
          title: "Section Added",
          description: "The section has been added to your schedule.",
        });
      } else {
        // Remove section from schedule
        await removeSectionFromSchedule(scheduleId, sectionId);

        toast({
          title: "Section Removed",
          description: "The section has been removed from your schedule.",
        });
      }

      // Call success callback
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error("Action failed");

      if (onError) {
        onError(err);
      }

      toast({
        title: "Error",
        description: err.message || `Failed to ${action} section`,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const buttonVariant = variant || (action === "remove" ? "destructive" : "default");

  return (
    <Button
      onClick={handleAction}
      disabled={disabled || loading}
      variant={buttonVariant}
      size={size}
      className={className}
    >
      {loading ? (
        <>
          <LoadingSpinner className="mr-2 h-4 w-4" />
          {action === "add" ? "Adding..." : "Removing..."}
        </>
      ) : (
        <>
          {action === "add" ? (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Add to Schedule
            </>
          ) : (
            <>
              <Trash2 className="mr-2 h-4 w-4" />
              Remove
            </>
          )}
        </>
      )}
    </Button>
  );
}
