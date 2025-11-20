import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import { 
  optimizeSchedule, 
  ScheduleOptimizationRequest,
  ScheduleOptimizationResponse 
} from "@/lib/api-endpoints";
import { useToast } from "@/components/ui/use-toast";
import { Progress } from "@/components/ui/progress";

export interface ScheduleConstraints {
  preferredDays?: string[];
  earliestStartTime?: string;
  latestEndTime?: string;
  minProfessorRating?: number;
  avoidGaps?: boolean;
}

interface OptimizeButtonProps {
  courseCodes: string[];
  semester?: string;
  constraints?: ScheduleConstraints;
  onOptimized: (response: ScheduleOptimizationResponse) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  className?: string;
}

export function OptimizeButton({
  courseCodes,
  semester = "Fall 2025",
  constraints,
  onOptimized,
  onError,
  disabled = false,
  className = "",
}: OptimizeButtonProps) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();

  const validateCourseCodes = (): boolean => {
    if (!courseCodes || courseCodes.length === 0) {
      toast({
        title: "No Courses Selected",
        description: "Please select at least one course to optimize.",
        variant: "destructive",
      });
      return false;
    }

    // Check if course codes are valid (not empty strings)
    const validCodes = courseCodes.filter(code => code && code.trim() !== "");
    if (validCodes.length === 0) {
      toast({
        title: "Invalid Courses",
        description: "Please provide valid course codes.",
        variant: "destructive",
      });
      return false;
    }

    return true;
  };

  const validateConstraints = (): boolean => {
    if (!constraints) {
      return true; // Constraints are optional
    }

    // Validate time constraints
    if (constraints.earliestStartTime && constraints.latestEndTime) {
      const earliest = new Date(`2000-01-01 ${constraints.earliestStartTime}`);
      const latest = new Date(`2000-01-01 ${constraints.latestEndTime}`);
      
      if (earliest >= latest) {
        toast({
          title: "Invalid Time Range",
          description: "Earliest start time must be before latest end time.",
          variant: "destructive",
        });
        return false;
      }
    }

    // Validate professor rating
    if (constraints.minProfessorRating !== undefined) {
      if (constraints.minProfessorRating < 0 || constraints.minProfessorRating > 5) {
        toast({
          title: "Invalid Rating",
          description: "Professor rating must be between 0 and 5.",
          variant: "destructive",
        });
        return false;
      }
    }

    return true;
  };

  const handleOptimize = async () => {
    if (!validateCourseCodes() || !validateConstraints()) {
      return;
    }

    setLoading(true);
    setProgress(0);

    // Simulate progress updates
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 300);

    try {
      const request: ScheduleOptimizationRequest = {
        courseCodes: courseCodes.filter(code => code && code.trim() !== ""),
        semester,
        constraints,
      };

      const response = await optimizeSchedule(request);

      clearInterval(progressInterval);
      setProgress(100);

      onOptimized(response);

      toast({
        title: "Optimization Complete",
        description: `Generated ${response.schedules.length} optimized schedule${response.schedules.length !== 1 ? 's' : ''}.`,
      });
    } catch (error) {
      clearInterval(progressInterval);
      const err = error instanceof Error ? error : new Error("Optimization failed");
      
      if (onError) {
        onError(err);
      }

      toast({
        title: "Optimization Failed",
        description: err.message || "Failed to optimize schedule. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 1000);
    }
  };

  return (
    <div className="space-y-2">
      <Button
        onClick={handleOptimize}
        disabled={disabled || loading || courseCodes.length === 0}
        className={`bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 ${className}`}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Optimizing...
          </>
        ) : (
          <>
            <Sparkles className="mr-2 h-4 w-4" />
            AI Optimize
          </>
        )}
      </Button>
      
      {loading && progress > 0 && (
        <Progress value={progress} className="h-2" />
      )}
    </div>
  );
}
