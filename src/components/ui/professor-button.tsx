import { useState } from "react";
import { Button } from "@/components/ui/button";
import { GraduationCap, Loader2 } from "lucide-react";
import { 
  getProfessorByIdAPI, 
  getProfessorByNameAPI,
  ProfessorDetails 
} from "@/lib/api-endpoints";
import { Skeleton } from "@/components/ui/loading-indicators";

interface ProfessorButtonProps {
  professorId?: string;
  professorName?: string;
  onDataLoaded: (professor: ProfessorDetails) => void;
  onError?: (error: Error) => void;
  variant?: "default" | "ghost" | "link";
  size?: "default" | "sm" | "lg";
  className?: string;
}

export function ProfessorButton({
  professorId,
  professorName,
  onDataLoaded,
  onError,
  variant = "link",
  size = "sm",
  className = "",
}: ProfessorButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (!professorId && !professorName) {
      return;
    }

    setLoading(true);

    try {
      let professor: ProfessorDetails;

      if (professorId) {
        professor = await getProfessorByIdAPI(professorId);
      } else if (professorName) {
        professor = await getProfessorByNameAPI(professorName);
      } else {
        throw new Error("No professor identifier provided");
      }

      onDataLoaded(professor);
    } catch (error) {
      const err = error instanceof Error ? error : new Error("Failed to load professor data");
      
      if (onError) {
        onError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Skeleton variant="rectangular" width="120px" height="32px" />;
  }

  return (
    <Button
      onClick={handleClick}
      variant={variant}
      size={size}
      className={`text-blue-600 hover:text-blue-700 ${className}`}
    >
      <GraduationCap className="mr-2 h-4 w-4" />
      {professorName || "View Professor"}
    </Button>
  );
}
