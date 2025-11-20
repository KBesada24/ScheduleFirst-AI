import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";
import { searchCourses, CourseWithSections } from "@/lib/supabase-queries";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export interface CourseFilters {
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
}

interface SearchButtonProps {
  query: string;
  filters: CourseFilters;
  onResults: (courses: CourseWithSections[]) => void;
  onError: (error: Error) => void;
  disabled?: boolean;
  className?: string;
  onClick?: () => void;
}

export function SearchButton({
  query,
  filters,
  onResults,
  onError,
  disabled = false,
  className = "",
  onClick,
}: SearchButtonProps) {
  const [loading, setLoading] = useState(false);

  const validateInputs = (): boolean => {
    // Query can be empty (search all), but filters should be valid
    if (filters.department && filters.department.trim() === "") {
      return false;
    }
    if (filters.semester && filters.semester.trim() === "") {
      return false;
    }
    if (filters.modality && filters.modality.trim() === "") {
      return false;
    }
    if (filters.timeSlot && filters.timeSlot.trim() === "") {
      return false;
    }
    return true;
  };

  const handleSearch = async () => {
    // Call optional onClick callback for validation
    if (onClick) {
      onClick();
    }

    if (!validateInputs()) {
      onError(new Error("Invalid search parameters"));
      return;
    }

    setLoading(true);
    try {
      const results = await searchCourses({
        query: query.trim() || undefined,
        department: filters.department !== "all" ? filters.department : undefined,
        semester: filters.semester || undefined,
        modality: filters.modality !== "all" ? filters.modality : undefined,
        timeSlot: filters.timeSlot !== "all" ? filters.timeSlot : undefined,
        limit: 50,
      });

      onResults(results);
    } catch (error) {
      onError(error instanceof Error ? error : new Error("Search failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      onClick={handleSearch}
      disabled={disabled || loading}
      className={`bg-blue-600 hover:bg-blue-700 ${className}`}
    >
      {loading ? (
        <>
          <LoadingSpinner className="mr-2 h-4 w-4" />
          Searching...
        </>
      ) : (
        <>
          <Search className="mr-2 h-4 w-4" />
          Search
        </>
      )}
    </Button>
  );
}
